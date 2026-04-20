from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, \
    create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .context import ChatContextManager
from ..types import Message


class Base(DeclarativeBase):
    pass


class DBMessage(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(index=True)
    message_id: Mapped[int] = mapped_column()
    sender_name: Mapped[str] = mapped_column()
    sender_shortname: Mapped[str] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column()
    text: Mapped[str] = mapped_column()


class ChatMetadata(Base):
    __tablename__ = "chat_metadata"

    chat_id: Mapped[int] = mapped_column(primary_key=True)
    context: Mapped[str] = mapped_column(default="")


class SQLiteChatContextManager(ChatContextManager):
    def __init__(self, db_url: str = 'sqlite+aiosqlite:///chat_history.db'):
        self.engine = create_async_engine(
            db_url,
            pool_size=5,
            max_overflow=0,
            pool_timeout=30
        )
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def initialize_db(self):
        """
        Create tables if they don't exist
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            await conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
            await conn.exec_driver_sql("PRAGMA cache_size=-100000;")

    async def get_last_messages(
        self,
        chat_id: int,
        limit: int | None,
    ) -> list[Message]:
        async with self.session_factory() as session:
            stmt = (
                select(DBMessage)
                .where(DBMessage.chat_id == chat_id)
                .order_by(desc(DBMessage.timestamp))
                .limit(limit)
            )
            result = await session.execute(stmt)
            db_messages = result.scalars().all()

            return [
                Message(
                    sender_name=m.sender_name,
                    sender_shortname=m.sender_shortname,
                    timestamp=m.timestamp,
                    message_id=m.message_id,
                    text=m.text
                ) for m in reversed(db_messages)
            ]

    async def append_message(self, chat_id: int, message: Message) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                db_msg = DBMessage(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    sender_name=message.sender_name,
                    sender_shortname=message.sender_shortname,
                    timestamp=message.timestamp,
                    text=message.text
                )
                session.add(db_msg)

    async def get_context(self, chat_id: int) -> str:
        async with self.session_factory() as session:
            stmt = select(ChatMetadata.context) \
                .where(ChatMetadata.chat_id == chat_id)
            result = await session.execute(stmt)
            context = result.scalar_one_or_none()
            return context if context is not None else ""

    async def update_chat_context(
        self,
        chat_id: int,
        new_context: str
    ) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                stmt = sqlite_insert(ChatMetadata).values(
                    chat_id=chat_id, 
                    context=new_context
                )
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=['chat_id'],  # Primary Key
                    set_=dict(context=new_context)
                )
                await session.execute(upsert_stmt)
