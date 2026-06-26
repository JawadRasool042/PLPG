"""
Reinforcement Learning module for PLPG.

This package layers an RL-based optimization on top of the existing
interest-prediction and quiz-generation pipeline. It does NOT replace
those systems – it consumes their outputs and decides the next-best
adaptive action (difficulty change, hint, topic switch, etc.).

Public surface:
    - RLService        : Orchestration entry point used by API + quiz routes
    - LearnerState     : Discretised state representation
    - Action           : Enumeration of available actions
    - QLearningAgent   : Tabular Q-learning implementation
    - RewardFunction   : Configurable reward design
    - RLRepository     : SQLite (PostgreSQL-ready) persistence layer
    - bp               : Flask blueprint exposing /api/rl/*
"""

from .schemas import (
    Action,
    ACTION_LIST,
    LearnerState,
    Decision,
    Transition,
    StepFeedback,
    EpisodeStatus,
)
from .state_builder import StateBuilder
from .reward import RewardFunction
from .q_learning import QLearningAgent
from .policy import Policy
from .environment import LearningEnvironment
from .storage import RLRepository
from .trainer import RLTrainer
from .service import RLService

__all__ = [
    "Action",
    "ACTION_LIST",
    "LearnerState",
    "Decision",
    "Transition",
    "StepFeedback",
    "EpisodeStatus",
    "StateBuilder",
    "RewardFunction",
    "QLearningAgent",
    "Policy",
    "LearningEnvironment",
    "RLRepository",
    "RLTrainer",
    "RLService",
]
