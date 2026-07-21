from enum import Enum


class TaskPhase(Enum):
    IDLE = 0
    APPROACH = 1
    GRASP = 2
    LIFT = 3
    RELEASE = 4