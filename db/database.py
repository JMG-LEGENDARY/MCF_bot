"""Gestion de la base de données SQLAlchemy"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import config
from db.models import Base
import logging

logger = logging.getLogger(__name__)


class Database:
    """Gestionnaire de base de données"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or config.DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            echo=config.DEBUG
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def init_db(self):
        """Crée toutes les tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ Base de données initialisée")
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager pour obtenir une session DB"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur DB: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Ferme la connexion à la DB"""
        self.engine.dispose()
        logger.info("🔌 Connexion DB fermée")


# Instance globale
db = Database()


# --- Helpers pour usage facile ---

def get_or_create_user(session: Session, discord_id: int):
    """Récupère ou crée un utilisateur"""
    from db.models import User
    user = session.query(User).filter(User.discord_id == discord_id).first()
    if not user:
        user = User(discord_id=discord_id)
        session.add(user)
        session.commit()
    return user


def add_transaction(session: Session, user_id: int, amount: float, transaction_type: str, 
                   description: str = None, base_amount: float = None, multiplier: float = 1.0):
    """Ajoute une transaction et met à jour le solde utilisateur"""
    from db.models import User, Transaction
    
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"Utilisateur {user_id} non trouvé")
        return None
    
    # Ajouter la transaction
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        description=description,
        base_amount=base_amount,
        multiplier_applied=multiplier
    )
    session.add(transaction)
    
    # Mettre à jour le solde
    user.craftycoin_balance += amount
    user.last_activity = __import__('datetime').datetime.utcnow()
    
    session.commit()
    logger.info(f"Transaction: user_id={user_id}, amount={amount}, type={transaction_type}")
    return transaction


def get_user_rank(session: Session, user_id: int) -> int:
    """Retourne le rang d'un utilisateur par nombre de coins"""
    from db.models import User
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return 0
    
    rank = session.query(User).filter(User.craftycoin_balance > user.craftycoin_balance).count()
    return rank + 1


def get_leaderboard(session: Session, limit: int = 10):
    """Retourne le classement des top utilisateurs"""
    from db.models import User
    return session.query(User).order_by(User.craftycoin_balance.desc()).limit(limit).all()
