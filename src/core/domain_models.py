"""
Domain models for the PMaC system.

These models represent the core business entities in the system,
independent of any specific external system like GitHub or Jira.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Union
from enum import Enum


class Status(str, Enum):
    """Status options for stories and other items."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


@dataclass
class Epic:
    """Represents a high-level grouping of stories."""
    id: str
    title: str
    description: str
    stories: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Epic':
        """Create an Epic instance from a dictionary."""
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            stories=data.get('stories', [])
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'stories': self.stories
        }


@dataclass
class Story:
    """Represents a user story or task."""
    id: str
    summary: str
    description: str
    epic_id: str
    story_points: int
    labels: List[str] = field(default_factory=list)
    status: str = Status.TODO
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Story':
        """Create a Story instance from a dictionary."""
        return cls(
            id=data.get('id', ''),
            summary=data.get('summary', ''),
            description=data.get('description', ''),
            epic_id=data.get('epic_id', ''),
            story_points=data.get('story_points', 0),
            labels=data.get('labels', []),
            status=data.get('status', Status.TODO)
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'summary': self.summary,
            'description': self.description,
            'epic_id': self.epic_id,
            'story_points': self.story_points,
            'labels': self.labels,
            'status': self.status
        }


@dataclass
class Sprint:
    """Represents a time-boxed iteration."""
    name: str
    start_date: date
    end_date: date
    stories: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Sprint':
        """Create a Sprint instance from a dictionary."""
        return cls(
            name=data.get('name', ''),
            start_date=date.fromisoformat(data.get('start_date', '2000-01-01')),
            end_date=date.fromisoformat(data.get('end_date', '2000-01-01')),
            stories=data.get('stories', [])
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'stories': self.stories
        }


@dataclass
class BoardColumn:
    """Represents a column in a board."""
    name: str
    stories: List[str] = field(default_factory=list)


@dataclass
class Board:
    """Represents a scrum or kanban board."""
    name: str
    type: str  # "scrum" or "kanban"
    columns: List[str] = field(default_factory=list)
    initial_assignments: Dict[str, List[str]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Board':
        """Create a Board instance from a dictionary."""
        board_data = data.get('board', {})
        return cls(
            name=board_data.get('name', ''),
            type=board_data.get('type', 'scrum'),
            columns=board_data.get('columns', []),
            initial_assignments=board_data.get('initial_assignments', {})
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'board': {
                'name': self.name,
                'type': self.type,
                'columns': self.columns,
                'initial_assignments': self.initial_assignments
            }
        }


@dataclass
class View:
    """Represents a view configuration for project visualization."""
    type: str
    name: str
    columns: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'View':
        """Create a View instance from a dictionary."""
        return cls(
            type=data.get('type', ''),
            name=data.get('name', ''),
            columns=data.get('columns', [])
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'type': self.type,
            'name': self.name,
            'columns': self.columns
        }


@dataclass
class ProjectMeta:
    """Project metadata."""
    project_key: str
    name: str
    description: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectMeta':
        """Create a ProjectMeta instance from a dictionary."""
        return cls(
            project_key=data.get('project_key', ''),
            name=data.get('name', ''),
            description=data.get('description', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'project_key': self.project_key,
            'name': self.name,
            'description': self.description
        }


@dataclass
class ProjectPlan:
    """Comprehensive project plan combining all elements."""
    project: ProjectMeta
    epics: List[Epic] = field(default_factory=list)
    stories: List[Story] = field(default_factory=list)
    sprints: List[Sprint] = field(default_factory=list)
    views: List[View] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectPlan':
        """Create a ProjectPlan instance from a dictionary."""
        return cls(
            project=ProjectMeta.from_dict(data.get('project', {})),
            epics=[Epic.from_dict(epic) for epic in data.get('epics', [])],
            stories=[Story.from_dict(story) for story in data.get('stories', [])],
            sprints=[Sprint.from_dict(sprint) for sprint in data.get('sprints', [])],
            views=[View.from_dict(view) for view in data.get('views', [])]
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'project': self.project.to_dict(),
            'epics': [epic.to_dict() for epic in self.epics],
            'stories': [story.to_dict() for story in self.stories],
            'sprints': [sprint.to_dict() for sprint in self.sprints],
            'views': [view.to_dict() for view in self.views]
        }
