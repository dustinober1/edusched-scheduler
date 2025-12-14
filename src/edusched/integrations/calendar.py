"""Calendar integration for EduSched.

Supports Google Calendar, Outlook Calendar, and generic iCal subscriptions.
Handles bulk operations, sync conflict resolution, and real-time updates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from edusched.domain.result import Result


@dataclass
class CalendarEvent:
    """Represents a calendar event."""

    id: str
    title: str
    description: str = ""
    start_time: datetime = None
    end_time: datetime = None
    location: str = ""
    attendees: List[str] = field(default_factory=list)
    calendar_id: str = ""
    external_id: str = ""  # ID in external calendar
    recurrence_rule: Optional[str] = None
    reminders: List[Dict[str, Any]] = field(default_factory=list)
    color: str = "#3174ad"  # Default blue

    # Course-specific fields
    course_code: str = ""
    section: str = ""
    instructor: str = ""
    room: str = ""

    # Sync status
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"  # pending, synced, error
    sync_errors: List[str] = field(default_factory=list)


@dataclass
class CalendarConnection:
    """Connection details for a calendar service."""

    service: str  # google, outlook, ical
    name: str
    calendar_id: str
    credentials: Dict[str, Any] = field(default_factory=dict)
    is_default: bool = False
    sync_enabled: bool = True
    last_sync: Optional[datetime] = None
    sync_frequency_minutes: int = 60

    # Permissions
    can_read: bool = True
    can_write: bool = True
    can_delete: bool = False

    # Sync settings
    include_students: bool = True
    include_teachers: bool = True
    include_rooms: bool = True
    create_recurring: bool = True
    conflict_resolution: str = "external_wins"  # external_wins, internal_wins, manual


class CalendarProvider(ABC):
    """Abstract base class for calendar providers."""

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the calendar service."""
        pass

    @abstractmethod
    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create an event and return its ID."""
        pass

    @abstractmethod
    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Update an existing event."""
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event by ID."""
        pass

    @abstractmethod
    def list_events(
        self, start_time: datetime, end_time: datetime, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """List events in a time range."""
        pass

    @abstractmethod
    def detect_conflicts(
        self, event: CalendarEvent, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """Detect conflicting events."""
        pass

    @abstractmethod
    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """Get list of available calendars."""
        pass


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar integration."""

    def __init__(self):
        self.service = None
        self.scopes = ["https://www.googleapis.com/auth/calendar"]

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Google Calendar API."""
        try:
            # Check if required libraries are available
            try:
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build
            except ImportError:
                return False

            # Handle different credential types
            if "access_token" in credentials:
                # Using OAuth tokens
                creds = Credentials(
                    token=credentials["access_token"],
                    refresh_token=credentials.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=credentials.get("client_id"),
                    client_secret=credentials.get("client_secret"),
                    scopes=self.scopes,
                )
            elif "service_account" in credentials:
                # Using service account
                # Implementation for service account auth
                return False

            # Build the service
            self.service = build("calendar", "v3", credentials=creds)
            return True

        except Exception as e:
            print(f"Google Calendar auth error: {e}")
            return False

    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create an event in Google Calendar."""
        if not self.service:
            return None

        try:
            # Convert to Google Calendar format
            event_body = {
                "summary": event.title,
                "description": event.description,
                "location": event.location,
                "start": {
                    "dateTime": event.start_time.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": event.end_time.isoformat(),
                    "timeZone": "UTC",
                },
                "attendees": [{"email": email} for email in event.attendees],
                "reminders": {
                    "useDefault": False,
                    "overrides": event.reminders,
                }
                if event.reminders
                else {"useDefault": True},
            }

            # Add color if specified
            if event.color:
                event_body["colorId"] = self._get_color_id(event.color)

            # Add recurrence if specified
            if event.recurrence_rule:
                event_body["recurrence"] = [event.recurrence_rule]

            # Create the event
            result = (
                self.service.events()
                .insert(calendarId=event.calendar_id or "primary", body=event_body)
                .execute()
            )

            return result.get("id")

        except Exception as e:
            print(f"Error creating Google Calendar event: {e}")
            return None

    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Update an event in Google Calendar."""
        if not self.service:
            return False

        try:
            # Get existing event
            existing = (
                self.service.events()
                .get(calendarId=event.calendar_id or "primary", eventId=event_id)
                .execute()
            )

            # Update fields
            existing["summary"] = event.title
            existing["description"] = event.description
            existing["location"] = event.location
            existing["start"]["dateTime"] = event.start_time.isoformat()
            existing["end"]["dateTime"] = event.end_time.isoformat()
            existing["attendees"] = [{"email": email} for email in event.attendees]

            # Update the event
            self.service.events().update(
                calendarId=event.calendar_id or "primary", eventId=event_id, body=existing
            ).execute()

            return True

        except Exception as e:
            print(f"Error updating Google Calendar event: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete an event from Google Calendar."""
        if not self.service:
            return False

        try:
            self.service.events().delete(calendarId="primary", eventId=event_id).execute()
            return True

        except Exception as e:
            print(f"Error deleting Google Calendar event: {e}")
            return False

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event from Google Calendar."""
        if not self.service:
            return None

        try:
            result = self.service.events().get(calendarId="primary", eventId=event_id).execute()

            # Convert to CalendarEvent
            event = CalendarEvent(
                id=result["id"],
                title=result["summary"],
                description=result.get("description", ""),
                start_time=datetime.fromisoformat(result["start"]["dateTime"]),
                end_time=datetime.fromisoformat(result["end"]["dateTime"]),
                location=result.get("location", ""),
                calendar_id="primary",
                external_id=result["id"],
            )

            # Add attendees
            if "attendees" in result:
                event.attendees = [a["email"] for a in result["attendees"]]

            return event

        except Exception as e:
            print(f"Error getting Google Calendar event: {e}")
            return None

    def list_events(
        self, start_time: datetime, end_time: datetime, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """List events from Google Calendar."""
        if not self.service:
            return []

        try:
            result = (
                self.service.events()
                .list(
                    calendarId=calendar_id or "primary",
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = []
            for item in result.get("items", []):
                event = CalendarEvent(
                    id=item["id"],
                    title=item["summary"],
                    description=item.get("description", ""),
                    start_time=datetime.fromisoformat(item["start"]["dateTime"]),
                    end_time=datetime.fromisoformat(item["end"]["dateTime"]),
                    location=item.get("location", ""),
                    calendar_id=calendar_id or "primary",
                    external_id=item["id"],
                )

                if "attendees" in item:
                    event.attendees = [a["email"] for a in item["attendees"]]

                events.append(event)

            return events

        except Exception as e:
            print(f"Error listing Google Calendar events: {e}")
            return []

    def detect_conflicts(
        self, event: CalendarEvent, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """Detect conflicts in Google Calendar."""
        # Get events in the same time range
        events = self.list_events(
            event.start_time - timedelta(minutes=15),
            event.end_time + timedelta(minutes=15),
            calendar_id,
        )

        # Check for overlaps
        conflicts = []
        for existing in events:
            if self._events_overlap(event, existing):
                conflicts.append(existing)

        return conflicts

    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """Get list of Google Calendars."""
        if not self.service:
            return []

        try:
            result = self.service.calendarList().list().execute()
            calendars = []

            for item in result.get("items", []):
                calendars.append(
                    {
                        "id": item["id"],
                        "name": item["summary"],
                        "primary": item.get("primary", False),
                        "access_role": item.get("accessRole", "reader"),
                    }
                )

            return calendars

        except Exception as e:
            print(f"Error getting Google Calendar list: {e}")
            return []

    def _get_color_id(self, color: str) -> str:
        """Map color to Google Calendar color ID."""
        # Google Calendar has predefined colors (1-11)
        color_map = {
            "#3174ad": "1",  # Blue
            "#e74c3c": "2",  # Red
            "#2ecc71": "3",  # Green
            "#f39c12": "4",  # Yellow
            "#9b59b6": "5",  # Purple
            "#1abc9c": "6",  # Teal
            "#34495e": "7",  # Gray
            "#e67e22": "8",  # Orange
            "#95a5a6": "9",  # Light Gray
            "#d35400": "10",  # Dark Orange
            "#c0392b": "11",  # Dark Red
        }
        return color_map.get(color.lower(), "1")

    def _events_overlap(self, event1: CalendarEvent, event2: CalendarEvent) -> bool:
        """Check if two events overlap."""
        return event1.start_time < event2.end_time and event2.start_time < event1.end_time


class OutlookCalendarProvider(CalendarProvider):
    """Outlook Calendar integration."""

    def __init__(self):
        self.service = None
        self.graph_api_url = "https://graph.microsoft.com/v1.0"

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Microsoft Graph API."""
        try:
            # Check if required libraries are available
            try:
                import requests
                from msal import ConfidentialClientApplication, PublicClientApplication
            except ImportError:
                print("MSAL and requests libraries required for Outlook integration")
                return False

            # Get access token
            if "client_id" in credentials and "client_secret" in credentials:
                # Confidential client (app-only)
                app = ConfidentialClientApplication(
                    client_id=credentials["client_id"],
                    client_credential=credentials["client_secret"],
                    authority="https://login.microsoftonline.com/"
                    + credentials.get("tenant_id", "common"),
                )
            else:
                # Public client (delegated)
                app = PublicClientApplication(
                    client_id=credentials["client_id"],
                    authority="https://login.microsoftonline.com/"
                    + credentials.get("tenant_id", "common"),
                )

            # Acquire token
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            if "access_token" not in result:
                return False

            self.access_token = result["access_token"]
            return True

        except Exception as e:
            print(f"Outlook Calendar auth error: {e}")
            return False

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make a request to Microsoft Graph API."""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            url = f"{self.graph_api_url}/{endpoint}"

            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return None

            if response.status_code < 400:
                return response.json()
            else:
                print(f"Outlook API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Outlook API request error: {e}")
            return None

    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create an event in Outlook Calendar."""
        event_body = {
            "subject": event.title,
            "body": {"contentType": "HTML", "content": event.description},
            "start": {"dateTime": event.start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": event.end_time.isoformat(), "timeZone": "UTC"},
            "location": {"displayName": event.location},
            "attendees": [
                {
                    "emailAddress": {"address": email, "name": email.split("@")[0]},
                    "type": "required",
                }
                for email in event.attendees
            ]
            if event.attendees
            else [],
        }

        result = self._make_request("POST", "me/events", event_body)
        return result.get("id") if result else None

    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Update an event in Outlook Calendar."""
        event_body = {
            "subject": event.title,
            "body": {"contentType": "HTML", "content": event.description},
            "start": {"dateTime": event.start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": event.end_time.isoformat(), "timeZone": "UTC"},
            "location": {"displayName": event.location},
        }

        result = self._make_request("PATCH", f"me/events/{event_id}", event_body)
        return result is not None

    def delete_event(self, event_id: str) -> bool:
        """Delete an event from Outlook Calendar."""
        result = self._make_request("DELETE", f"me/events/{event_id}")
        return result is not None

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event from Outlook Calendar."""
        result = self._make_request("GET", f"me/events/{event_id}")
        if not result:
            return None

        return CalendarEvent(
            id=result["id"],
            title=result["subject"],
            description=result["body"].get("content", ""),
            start_time=datetime.fromisoformat(result["start"]["dateTime"]),
            end_time=datetime.fromisoformat(result["end"]["dateTime"]),
            location=result["location"].get("displayName", ""),
            external_id=result["id"],
        )

    def list_events(
        self, start_time: datetime, end_time: datetime, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """List events from Outlook Calendar."""
        filter_str = f"start/dateTime ge '{start_time.isoformat()}' and end/dateTime le '{end_time.isoformat()}'"
        result = self._make_request("GET", f"me/events?$filter={filter_str}")

        if not result:
            return []

        events = []
        for item in result.get("value", []):
            event = CalendarEvent(
                id=item["id"],
                title=item["subject"],
                description=item["body"].get("content", ""),
                start_time=datetime.fromisoformat(item["start"]["dateTime"]),
                end_time=datetime.fromisoformat(item["end"]["dateTime"]),
                location=item["location"].get("displayName", ""),
                external_id=item["id"],
            )
            events.append(event)

        return events

    def detect_conflicts(
        self, event: CalendarEvent, calendar_id: str = None
    ) -> List[CalendarEvent]:
        """Detect conflicts in Outlook Calendar."""
        events = self.list_events(
            event.start_time - timedelta(minutes=15),
            event.end_time + timedelta(minutes=15),
            calendar_id,
        )

        conflicts = []
        for existing in events:
            if self._events_overlap(event, existing):
                conflicts.append(existing)

        return conflicts

    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """Get list of Outlook Calendars."""
        result = self._make_request("GET", "me/calendars")
        if not result:
            return []

        calendars = []
        for item in result.get("value", []):
            calendars.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "primary": item.get("isDefaultCalendar", False),
                    "can_edit": item.get("canEdit", False),
                }
            )

        return calendars

    def _events_overlap(self, event1: CalendarEvent, event2: CalendarEvent) -> bool:
        """Check if two events overlap."""
        return event1.start_time < event2.end_time and event2.start_time < event1.end_time


class CalendarManager:
    """Manages calendar integrations and synchronization."""

    def __init__(self):
        self.providers = {
            "google": GoogleCalendarProvider(),
            "outlook": OutlookCalendarProvider(),
        }
        self.connections: Dict[str, CalendarConnection] = {}
        self.events: Dict[str, CalendarEvent] = {}  # Internal_id -> CalendarEvent
        self.sync_history: List[Dict[str, Any]] = []

    def add_connection(self, connection: CalendarConnection) -> bool:
        """Add a calendar connection."""
        provider = self.providers.get(connection.service)
        if not provider:
            return False

        # Authenticate
        if not provider.authenticate(connection.credentials):
            return False

        self.connections[connection.name] = connection
        return True

    def export_schedule(
        self, result: Result, connection_name: str, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Export a schedule to a calendar."""
        connection = self.connections.get(connection_name)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        provider = self.providers.get(connection.service)
        if not provider:
            return {"success": False, "error": "Provider not found"}

        options = options or {}
        created_events = []
        failed_events = []
        conflicts = []

        for assignment in result.assignments:
            # Create calendar event
            event = self._assignment_to_event(assignment, connection, options)

            # Check for conflicts if requested
            if options.get("check_conflicts", True):
                existing_conflicts = provider.detect_conflicts(event, connection.calendar_id)
                if existing_conflicts:
                    conflicts.append(
                        {"event": event.title, "conflicts": [c.title for c in existing_conflicts]}
                    )

                    # Handle conflict based on resolution strategy
                    if connection.conflict_resolution == "external_wins":
                        continue  # Skip this event
                    elif connection.conflict_resolution == "internal_wins":
                        # Delete external conflicts
                        for conflict in existing_conflicts:
                            provider.delete_event(conflict.external_id)
                    else:  # manual
                        failed_events.append(
                            {"event": event.title, "error": "Manual conflict resolution required"}
                        )
                        continue

            # Create the event
            external_id = provider.create_event(event)
            if external_id:
                event.external_id = external_id
                event.sync_status = "synced"
                event.last_sync = datetime.now()
                created_events.append(event)
                self.events[event.id] = event
            else:
                event.sync_status = "error"
                event.sync_errors.append("Failed to create event")
                failed_events.append(
                    {"event": event.title, "error": "Failed to create in external calendar"}
                )

        # Record sync
        sync_record = {
            "timestamp": datetime.now(),
            "connection": connection_name,
            "events_exported": len(created_events),
            "events_failed": len(failed_events),
            "conflicts_found": len(conflicts),
        }
        self.sync_history.append(sync_record)

        return {
            "success": len(created_events) > 0,
            "created": len(created_events),
            "failed": len(failed_events),
            "conflicts": len(conflicts),
            "events": created_events,
            "conflict_details": conflicts,
            "failed_details": failed_events,
        }

    def sync_schedule(
        self, result: Result, connection_name: str, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Two-way sync between internal and external calendar."""
        connection = self.connections.get(connection_name)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        provider = self.providers.get(connection.service)
        if not provider:
            return {"success": False, "error": "Provider not found"}

        options = options or {}
        sync_window = options.get("sync_window_days", 30)
        start_date = datetime.now() - timedelta(days=sync_window)
        end_date = datetime.now() + timedelta(days=sync_window)

        # Get external events
        external_events = provider.list_events(start_date, end_date, connection.calendar_id)

        # Build mapping of external events
        external_map = {e.external_id: e for e in self.events.values() if e.external_id}

        # Sync changes
        updates = []
        creates = []
        deletes = []

        for ext_event in external_events:
            if ext_event.external_id in external_map:
                # Event exists in both - check for updates
                internal_event = external_map[ext_event.external_id]
                if self._has_event_changed(internal_event, ext_event):
                    updates.append((internal_event, ext_event))
            else:
                # External-only event
                if options.get("import_external", False):
                    # Import to internal
                    internal_id = f"imported_{ext_event.external_id}"
                    ext_event.id = internal_id
                    creates.append(ext_event)

        # Check for internal-only events
        for assignment in result.assignments:
            event = self._assignment_to_event(assignment, connection, options)
            if event.id not in [e.id for e in external_events]:
                if event.external_id:
                    # Was external but no longer exists - might have been deleted
                    deletes.append(event)

        # Apply changes
        created_count = 0
        updated_count = 0
        deleted_count = 0

        for event in creates:
            self.events[event.id] = event
            created_count += 1

        for internal, external in updates:
            # Update external with internal data
            if provider.update_event(external.external_id, internal):
                updated_count += 1

        for event in deletes:
            if provider.delete_event(event.external_id):
                del self.events[event.id]
                deleted_count += 1

        return {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "deleted": deleted_count,
            "external_total": len(external_events),
            "internal_total": len(self.events),
        }

    def _assignment_to_event(
        self, assignment: Any, connection: CalendarConnection, options: Dict[str, Any]
    ) -> CalendarEvent:
        """Convert assignment to calendar event."""
        request = assignment.request if hasattr(assignment, "request") else None
        resource = assignment.resource if hasattr(assignment, "resource") else None

        # Build title
        title = "Class"
        if request:
            if hasattr(request, "course_code"):
                title = request.course_code
            if hasattr(request, "section"):
                title += f" - {request.section}"

        # Build description
        description = []
        if request:
            if hasattr(request, "department_id"):
                description.append(f"Department: {request.department_id}")
            if hasattr(request, "enrollment_count"):
                description.append(f"Enrollment: {request.enrollment_count}")

        # Add instructor
        instructor = ""
        if request and hasattr(request, "teacher_id"):
            instructor = request.teacher_id
            if connection.include_teachers:
                description.append(f"Instructor: {instructor}")

        # Add location
        location = ""
        if resource:
            if hasattr(resource, "name"):
                location = resource.name
            elif hasattr(resource, "building_id"):
                location = f"Building {resource.building_id}"

        # Build attendees
        attendees = []
        if instructor and connection.include_teachers:
            attendees.append(instructor)
        if request and connection.include_students and hasattr(request, "enrolled_students"):
            attendees.extend(request.enrolled_students)

        # Create event
        event = CalendarEvent(
            id=str(assignment.id),
            title=title,
            description="\n".join(description),
            start_time=assignment.start_time,
            end_time=assignment.start_time + (request.duration if request else timedelta(hours=1)),
            location=location,
            attendees=attendees,
            calendar_id=connection.calendar_id,
            course_code=getattr(request, "course_code", "") if request else "",
            instructor=instructor,
            room=location,
        )

        # Add recurring rule if applicable
        if (
            options.get("create_recurring", False)
            and request
            and hasattr(request, "number_of_occurrences")
        ):
            if request.number_of_occurrences > 1:
                # Simplified recurrence - would need proper RRULE generation
                event.recurrence_rule = f"RRULE:FREQ=WEEKLY;COUNT={request.number_of_occurrences}"

        return event

    def _has_event_changed(self, internal: CalendarEvent, external: CalendarEvent) -> bool:
        """Check if an event has changed compared to external version."""
        return (
            internal.title != external.title
            or internal.description != external.description
            or internal.start_time != external.start_time
            or internal.end_time != external.end_time
            or internal.location != external.location
        )

    def generate_ical_url(self, result: Result, options: Dict[str, Any] = None) -> str:
        """Generate an iCal subscription URL for the schedule."""
        # This would typically create a web endpoint that serves iCal data
        # For now, return a placeholder URL
        base_url = options.get("base_url", "https://edusched.example.com")
        schedule_id = options.get("schedule_id", "default")
        return f"{base_url}/ical/{schedule_id}?token=abc123"

    def create_webhook_subscription(
        self,
        connection_name: str,
        webhook_url: str,
        expiration_hours: int = 4230,  # Max allowed by most APIs
    ) -> Optional[Dict[str, Any]]:
        """Create a webhook subscription for real-time updates."""
        connection = self.connections.get(connection_name)
        if not connection or connection.service != "outlook":
            return None  # Webhooks primarily supported by Outlook

        provider = self.providers["outlook"]

        subscription_body = {
            "changeType": "created,updated,deleted",
            "notificationUrl": webhook_url,
            "resource": "me/events",
            "expirationDateTime": (datetime.now() + timedelta(hours=expiration_hours)).isoformat(),
            "clientState": "edusched_client",
        }

        result = provider._make_request("POST", "me/subscriptions", subscription_body)
        return result if result else None
