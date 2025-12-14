"""Notification system for EduSched.

Handles email notifications, in-app notifications, digest generation,
and multi-channel delivery with preferences and scheduling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from edusched.domain.result import Result


class NotificationType(Enum):
    """Types of notifications."""

    SCHEDULE_CHANGED = "schedule_changed"
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_CANCELLED = "assignment_cancelled"
    ROOM_CHANGED = "room_changed"
    TIME_CHANGED = "time_changed"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    SYSTEM_MAINTENANCE = "system_maintenance"
    NEW_COURSE_AVAILABLE = "new_course_available"
    ENROLLMENT_OPEN = "enrollment_open"
    DEADLINE_REMINDER = "deadline_reminder"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_SUMMARY = "weekly_summary"


class NotificationChannel(Enum):
    """Available notification channels."""

    EMAIL = "email"
    IN_APP = "in_app"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationMessage:
    """Represents a notification message."""

    id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority

    # Targeting
    recipient_ids: List[str] = field(default_factory=list)  # User IDs
    role_filters: List[str] = field(default_factory=list)  # Role-based targeting
    department_filters: List[str] = field(default_factory=list)

    # Content
    details: Dict[str, Any] = field(default_factory=dict)
    action_url: Optional[str] = None
    action_text: Optional[str] = None

    # Delivery
    channels: List[NotificationChannel] = field(default_factory=list)
    send_immediately: bool = True
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    delivery_status: Dict[str, str] = field(default_factory=dict)  # channel -> status

    # Metadata
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class NotificationPreferences:
    """User notification preferences."""

    user_id: str
    email: str = ""
    phone: str = ""

    # Channel preferences
    email_enabled: bool = True
    in_app_enabled: bool = True
    sms_enabled: bool = False
    webhook_url: Optional[str] = None

    # Type preferences
    disabled_types: Set[NotificationType] = field(default_factory=set)
    high_priority_only: Set[NotificationType] = field(default_factory=set)

    # Timing preferences
    digest_frequency: str = "daily"  # immediate, daily, weekly, never
    digest_time: str = "09:00"  # HH:MM format
    quiet_hours_start: Optional[str] = None  # HH:MM
    quiet_hours_end: Optional[str] = None  # HH:MM
    timezone: str = "UTC"

    # Content preferences
    include_details: bool = True
    include_actions: bool = True
    max_daily_notifications: int = 50


@dataclass
class NotificationTemplate:
    """Template for generating notifications."""

    template_id: str
    type: NotificationType
    default_title: str
    default_message: str
    placeholders: List[str] = field(default_factory=list)
    required_placeholders: List[str] = field(default_factory=list)

    # Channel-specific templates
    email_template: Optional[str] = None
    sms_template: Optional[str] = None
    webhook_template: Optional[str] = None


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    def send(self, message: NotificationMessage, recipients: List[str]) -> Dict[str, Any]:
        """Send notification through this provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities."""
        pass


class EmailNotificationProvider(NotificationProvider):
    """Email notification provider using SMTP or email service."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_server = None
        self.email_service = config.get("service", "smtp")  # smtp, sendgrid, ses, etc.

    def send(self, message: NotificationMessage, recipients: List[str]) -> Dict[str, Any]:
        """Send email notification."""
        try:
            if self.email_service == "smtp":
                return self._send_smtp(message, recipients)
            elif self.email_service == "sendgrid":
                return self._send_sendgrid(message, recipients)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported email service: {self.email_service}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _send_smtp(self, message: NotificationMessage, recipients: List[str]) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.config["from_address"]
            msg["Subject"] = message.title
            msg["To"] = ", ".join(recipients)

            # Add HTML version if available
            if message.details.get("html_body"):
                msg.attach(MIMEText(message.details["html_body"], "html"))
            else:
                body = self._format_email_body(message)
                msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["smtp_user"], self.config["smtp_password"])
                server.send_message(msg)

            return {"success": True, "recipients": len(recipients)}

        except ImportError:
            return {"success": False, "error": "SMTP libraries not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _send_sendgrid(self, message: NotificationMessage, recipients: List[str]) -> Dict[str, Any]:
        """Send email via SendGrid."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(self.config["sendgrid_api_key"])

            for recipient in recipients:
                mail = Mail(
                    Email(self.config["from_address"]),
                    To(recipient),
                    message.title,
                    Content("text/plain", message.message),
                )

                # Add HTML content if available
                if message.details.get("html_body"):
                    mail.add_content(Content("text/html", message.details["html_body"]))

                sg.client.mail.send.post(request_body=mail.get())

            return {"success": True, "recipients": len(recipients)}

        except ImportError:
            return {"success": False, "error": "SendGrid library not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_email_body(self, message: NotificationMessage) -> str:
        """Format message for email."""
        body = f"{message.message}\n\n"

        if message.details and message.details.get("details"):
            body += "Details:\n"
            for key, value in message.details["details"].items():
                body += f"- {key}: {value}\n"

        if message.action_url:
            body += f"\n{message.action_text}: {message.action_url}"

        return body

    def is_available(self) -> bool:
        """Check if email provider is configured."""
        return (
            self.email_service == "smtp"
            and all(k in self.config for k in ["smtp_host", "smtp_user", "smtp_password"])
        ) or (
            self.email_service in ["sendgrid", "ses"]
            and f"{self.email_service}_api_key" in self.config
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """Get email provider information."""
        return {
            "name": "Email Provider",
            "service": self.email_service,
            "available": self.is_available(),
            "supports_html": True,
            "supports_attachments": False,
        }


class InAppNotificationProvider(NotificationProvider):
    """In-app notification provider."""

    def __init__(self):
        self.storage = {}  # In-memory storage - would use database in production

    def send(self, message: NotificationMessage, recipients: List[str]) -> Dict[str, Any]:
        """Store in-app notifications."""
        results = {"success": True, "recipients": []}

        for recipient_id in recipients:
            if recipient_id not in self.storage:
                self.storage[recipient_id] = []

            # Create notification record
            notification = {
                "id": message.id,
                "title": message.title,
                "message": message.message,
                "type": message.type.value,
                "priority": message.priority.value,
                "details": message.details,
                "action_url": message.action_url,
                "action_text": message.action_text,
                "created_at": message.created_at.isoformat(),
                "read": False,
                "read_at": None,
            }

            self.storage[recipient_id].append(notification)
            results["recipients"].append(recipient_id)

        return results

    def get_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        notifications = self.storage.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n["read"]]

        # Sort by created_at (newest first) and limit
        notifications.sort(key=lambda n: datetime.fromisoformat(n["created_at"]), reverse=True)

        return notifications[:limit]

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        if user_id in self.storage:
            for notification in self.storage[user_id]:
                if notification["id"] == notification_id:
                    notification["read"] = True
                    notification["read_at"] = datetime.now().isoformat()
                    return True
        return False

    def is_available(self) -> bool:
        """In-app provider is always available."""
        return True

    def get_provider_info(self) -> Dict[str, Any]:
        """Get in-app provider information."""
        return {
            "name": "In-App Provider",
            "available": True,
            "supports_actions": True,
            "supports_marking_read": True,
        }


class NotificationManager:
    """Manages all notification operations."""

    def __init__(self):
        self.providers: Dict[NotificationChannel, NotificationProvider] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.preferences: Dict[str, NotificationPreferences] = {}
        self.notification_history: List[Dict[str, Any]] = []

        # Default providers
        self.add_provider(NotificationChannel.EMAIL, EmailNotificationProvider({}))
        self.add_provider(NotificationChannel.IN_APP, InAppNotificationProvider())

        # Load default templates
        self._load_default_templates()

    def add_provider(self, channel: NotificationChannel, provider: NotificationProvider):
        """Add a notification provider."""
        self.providers[channel] = provider

    def configure_email(self, config: Dict[str, Any]) -> bool:
        """Configure email provider."""
        email_provider = EmailNotificationProvider(config)
        if email_provider.is_available():
            self.providers[NotificationChannel.EMAIL] = email_provider
            return True
        return False

    def send_notification(
        self, message: NotificationMessage, recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send notification to recipients."""
        recipients = recipients or message.recipient_ids

        # Apply user preferences
        filtered_recipients = self._apply_preferences(message, recipients)

        # Filter by available channels
        available_channels = [
            channel
            for channel in message.channels
            if channel in self.providers and self.providers[channel].is_available()
        ]

        if not available_channels:
            return {"success": False, "error": "No available channels"}

        results = {
            "success": True,
            "notification_id": message.id,
            "recipients": len(filtered_recipients),
            "channels": [],
            "errors": [],
        }

        # Send through each channel
        for channel in available_channels:
            provider = self.providers[channel]
            channel_result = provider.send(message, filtered_recipients)

            results["channels"].append(
                {
                    "channel": channel.value,
                    "result": channel_result,
                    "success": channel_result.get("success", False),
                }
            )

            if not channel_result.get("success", False):
                results["errors"].append(
                    f"{channel.value}: {channel_result.get('error', 'Unknown error')}"
                )

        # Update message status
        message.sent_at = datetime.now()
        for channel_result in results["channels"]:
            message.delivery_status[channel_result["channel"]] = (
                "sent" if channel_result["success"] else "failed"
            )

        # Record in history
        self.notification_history.append(
            {
                "timestamp": datetime.now(),
                "message_id": message.id,
                "type": message.type.value,
                "recipients": len(filtered_recipients),
                "channels": results["channels"],
                "success": results["success"],
            }
        )

        return results

    def send_template_notification(
        self, template_id: str, data: Dict[str, Any], recipients: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Send notification using a template."""
        template = self.templates.get(template_id)
        if not template:
            return {"success": False, "error": f"Template {template_id} not found"}

        # Validate required placeholders
        for placeholder in template.required_placeholders:
            if placeholder not in data:
                return {"success": False, "error": f"Required placeholder {placeholder} missing"}

        # Generate message
        message = self._generate_message_from_template(template, data, **kwargs)

        # Send
        return self.send_notification(message, recipients)

    def set_user_preferences(self, preferences: NotificationPreferences):
        """Set notification preferences for a user."""
        self.preferences[preferences.user_id] = preferences

    def get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get notification preferences for a user."""
        if user_id not in self.preferences:
            self.preferences[user_id] = NotificationPreferences(user_id=user_id)
        return self.preferences[user_id]

    def schedule_digest(self, user_id: str, digest_type: str = "daily") -> bool:
        """Schedule digest for a user."""
        preferences = self.get_user_preferences(user_id)
        if preferences.digest_frequency == digest_type:
            # In production, this would create a scheduled task
            return True
        return False

    def generate_digest(
        self, user_id: str, digest_type: str = "daily", start_time: Optional[datetime] = None
    ) -> Optional[NotificationMessage]:
        """Generate digest notification for a user."""
        preferences = self.get_user_preferences(user_id)

        if preferences.digest_frequency == "never":
            return None

        # Get in-app notifications for digest
        in_app_provider = self.providers.get(NotificationChannel.IN_APP)
        if not in_app_provider:
            return None

        if not start_time:
            start_time = datetime.now() - timedelta(days=1)

        notifications = in_app_provider.get_notifications(user_id, unread_only=True)

        if not notifications:
            return None

        # Create digest message
        digest_message = NotificationMessage(
            id=f"digest_{user_id}_{datetime.now().timestamp()}",
            type=NotificationType.WEEKLY_SUMMARY
            if digest_type == "weekly"
            else NotificationType.DAILY_DIGEST,
            title=f"Your {digest_type.capitalize} Schedule Digest",
            message=f"You have {len(notifications)} new notification{'s' if len(notifications) != 1 else ''}",
            priority=NotificationPriority.LOW,
            recipient_ids=[user_id],
            channels=[NotificationChannel.EMAIL]
            if preferences.email_enabled
            else [NotificationChannel.IN_APP],
            details={
                "notification_count": len(notifications),
                "notifications": notifications[:10],  # Limit to 10 for digest
                "digest_type": digest_type,
            },
        )

        return digest_message

    def send_schedule_change_notifications(
        self, result: Result, changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send notifications for schedule changes."""
        notifications_sent = 0
        errors = []

        for change in changes:
            # Create notification based on change type
            if change.get("type") == "assignment_created":
                message = NotificationMessage(
                    id=f"new_assignment_{datetime.now().timestamp()}",
                    type=NotificationType.ASSIGNMENT_CREATED,
                    title="New Class Scheduled",
                    message=f"Your class {change.get('course_code', 'Unknown')} has been scheduled",
                    priority=NotificationPriority.MEDIUM,
                    recipient_ids=self._get_affected_recipients(change),
                    channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                    details=change,
                )
            elif change.get("type") == "assignment_cancelled":
                message = NotificationMessage(
                    id=f"cancelled_assignment_{datetime.now().timestamp()}",
                    type=NotificationType.ASSIGNMENT_CANCELLED,
                    title="Class Cancelled",
                    message=f"Your class {change.get('course_code', 'Unknown')} has been cancelled",
                    priority=NotificationPriority.HIGH,
                    recipient_ids=self._get_affected_recipients(change),
                    channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                    details=change,
                )
            else:
                # Generic change notification
                message = NotificationMessage(
                    id=f"schedule_change_{datetime.now().timestamp()}",
                    type=NotificationType.SCHEDULE_CHANGED,
                    title="Schedule Updated",
                    message=f"Your schedule has been updated: {change.get('description', '')}",
                    priority=NotificationPriority.MEDIUM,
                    recipient_ids=self._get_affected_recipients(change),
                    channels=[NotificationChannel.IN_APP],
                    details=change,
                )

            # Send notification
            result = self.send_notification(message)
            if result["success"]:
                notifications_sent += 1
            else:
                errors.extend(result.get("errors", []))

        return {
            "success": len(errors) == 0,
            "notifications_sent": notifications_sent,
            "errors": errors,
        }

    def _apply_preferences(self, message: NotificationMessage, recipients: List[str]) -> List[str]:
        """Apply user preferences to recipient list."""
        filtered = []

        for recipient_id in recipients:
            preferences = self.get_user_preferences(recipient_id)

            # Check if type is disabled
            if message.type in preferences.disabled_types:
                continue

            # Check if only high priority for this type
            if (
                message.type in preferences.high_priority_only
                and message.priority != NotificationPriority.HIGH
                and message.priority != NotificationPriority.URGENT
            ):
                continue

            # Check quiet hours
            if (
                self._is_quiet_hours(preferences)
                and message.priority != NotificationPriority.URGENT
            ):
                # Schedule for later instead of sending now
                continue

            filtered.append(recipient_id)

        return filtered

    def _is_quiet_hours(self, preferences: NotificationPreferences) -> bool:
        """Check if current time is within quiet hours."""
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False

        now = datetime.now()
        current_time = now.time()

        # Parse quiet hours
        start_parts = preferences.quiet_hours_start.split(":")
        end_parts = preferences.quiet_hours_end.split(":")

        try:
            start_time = datetime(
                now.year, now.month, now.day, int(start_parts[0]), int(start_parts[1])
            ).time()
            end_time = datetime(
                now.year, now.month, now.day, int(end_parts[0]), int(end_parts[1])
            ).time()

            return start_time <= current_time <= end_time
        except Exception:
            return False

    def _get_affected_recipients(self, change: Dict[str, Any]) -> List[str]:
        """Get list of affected recipients for a change."""
        recipients = []

        # Add affected students
        if "students" in change:
            recipients.extend(change["students"])

        # Add instructor
        if "instructor" in change:
            recipients.append(change["instructor"])

        # Add department admins
        if "department" in change:
            # Would need to lookup department admin users
            pass

        return list(set(recipients))  # Remove duplicates

    def _generate_message_from_template(
        self, template: NotificationTemplate, data: Dict[str, Any], **kwargs
    ) -> NotificationMessage:
        """Generate notification message from template."""
        # Replace placeholders
        title = template.default_title
        message = template.default_message

        for placeholder in template.placeholders:
            value = str(data.get(placeholder, ""))
            title = title.replace(f"{{{placeholder}}}", value)
            message = message.replace(f"{{{placeholder}}}", value)

        return NotificationMessage(
            id=f"template_{template.template_id}_{datetime.now().timestamp()}",
            type=template.type,
            title=title,
            message=message,
            priority=kwargs.get("priority", NotificationPriority.MEDIUM),
            recipient_ids=kwargs.get("recipient_ids", []),
            channels=kwargs.get("channels", [NotificationChannel.IN_APP]),
            details=data,
        )

    def _load_default_templates(self):
        """Load default notification templates."""
        # Schedule change template
        self.templates["schedule_changed"] = NotificationTemplate(
            template_id="schedule_changed",
            type=NotificationType.SCHEDULE_CHANGED,
            default_title="Schedule Updated",
            default_message="Your schedule for {course_code} has been updated.",
            placeholders=["course_code"],
            required_placeholders=["course_code"],
        )

        # Assignment created template
        self.templates["assignment_created"] = NotificationTemplate(
            template_id="assignment_created",
            type=NotificationType.ASSIGNMENT_CREATED,
            default_title="New Class Scheduled",
            default_message="Your class {course_code} has been scheduled for {time} in {room}.",
            placeholders=["course_code", "time", "room"],
            required_placeholders=["course_code"],
        )

        # Conflict detected template
        self.templates["conflict_detected"] = NotificationTemplate(
            template_id="conflict_detected",
            type=NotificationType.CONFLICT_DETECTED,
            default_title="Schedule Conflict",
            default_message="A conflict has been detected in your schedule involving {conflict_type}.",
            placeholders=["conflict_type"],
            required_placeholders=["conflict_type"],
        )
