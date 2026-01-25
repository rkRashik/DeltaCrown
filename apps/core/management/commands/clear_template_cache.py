"""
Management command to clear Django's template cache.
Usage: python manage.py clear_template_cache
"""
from django.core.management.base import BaseCommand
from django.template import engines
from django.template.loaders.cached import Loader as CachedLoader


class Command(BaseCommand):
    help = 'Clear Django template cache'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Clearing template cache...'))
        
        cleared_count = 0
        
        for engine in engines.all():
            if hasattr(engine, 'engine'):
                # Clear template cache for this engine
                if hasattr(engine.engine, 'template_loaders'):
                    for loader in engine.engine.template_loaders:
                        if isinstance(loader, CachedLoader):
                            loader.reset()
                            cleared_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Cleared cache for {loader.__class__.__name__}')
                            )
                
                # Also try to clear the get_template cache
                if hasattr(engine.engine, 'get_template_cache'):
                    cache = getattr(engine.engine, 'get_template_cache', None)
                    if cache:
                        cache.clear()
                        cleared_count += 1
                        self.stdout.write(
                            self.style.SUCCESS('✓ Cleared get_template_cache')
                        )
        
        if cleared_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠ No cached loaders found. Template caching may not be enabled.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Template cache cleared! ({cleared_count} caches)')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n💡 Refresh your browser to see the changes.')
        )
