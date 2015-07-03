from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class User(Base):
    """
    ユーザーテーブル
    """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    password = Column(Text)


class ControllerSettings(Base):
    """
    コントローラー設定テーブル
    """
    __tablename__ = 'setting'
    user = Column(Text, primary_key=True)
    power_pack = Column(Integer)
    turnout = Column(Integer)
    feeder = Column(Integer)



from pyramid.security import (
    Allow,
    Everyone,
    )

class RootFactory(object):
    """
    アクセス制御リスト
    """
    __acl__ = [ (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass

