"""
Management command: run_birthday_campaigns
------------------------------------------
Finds all birthday-type campaigns (status=draft) and sends to users
whose birthday is TODAY.

Usage:
    python manage.py run_birthday_campaigns

PythonAnywhere scheduled task (run daily at 8 AM):
    source /home/youruser/venv/bin/activate && cd /home/youruser/mallowback && python manage.py run_birthday_campaigns
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = "Send birthday campaigns to users whose birthday is today"

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f"[{timezone.now()}] Running birthday campaigns for {today}...")

        from notifications.models import Campaign
        from django.contrib.auth import get_user_model
        from notifications.campaign_services import send_campaign_to_user

        User = get_user_model()
        birthday_users = User.objects.filter(
            is_active=True,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        )

        count = birthday_users.count()
        self.stdout.write(f"  Found {count} users with birthday today")

        if count == 0:
            self.stdout.write("  No birthdays today. Done.")
            return

        # Get all active birthday campaigns
        campaigns = Campaign.objects.filter(campaign_type='birthday', status='draft')
        if not campaigns.exists():
            self.stdout.write("  No birthday campaigns configured. Create one in the admin panel.")
            return

        total_sent = 0
        for campaign in campaigns:
            self.stdout.write(f"  Running campaign: {campaign.name}")
            sent = 0
            for user in birthday_users:
                try:
                    result = send_campaign_to_user(campaign, user)
                    if result['sent']:
                        sent += 1
                        self.stdout.write(f"    ✓ Sent to {user.email} via {result['channels']}")
                except Exception as e:
                    self.stdout.write(f"    ✗ Failed for {user.email}: {e}")

            # Update stats but keep status=draft so it runs again next year
            campaign.total_recipients = count
            campaign.sent_count = sent
            campaign.sent_at = timezone.now()
            campaign.save(update_fields=['total_recipients', 'sent_count', 'sent_at'])
            total_sent += sent

        self.stdout.write(self.style.SUCCESS(
            f"  Birthday campaigns done: {total_sent} messages sent to {count} users"
        ))