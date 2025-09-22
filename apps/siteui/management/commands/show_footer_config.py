from django.core.management.base import BaseCommand
from apps.siteui.config_manager import print_config_summary

class Command(BaseCommand):
    help = 'Display current footer and social media configuration'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('DeltaCrown Footer Configuration')
        )
        print_config_summary()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.WARNING('To update configuration:')
        )
        self.stdout.write("1. Edit apps/siteui/social_config.py directly")
        self.stdout.write("2. Update URLs, enable/disable platforms, change text")
        self.stdout.write("3. Restart your Django server to see changes")
        self.stdout.write("\n" + self.style.SUCCESS('Configuration file location:'))
        self.stdout.write("   apps/siteui/social_config.py")