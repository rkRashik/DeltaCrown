"""
Management command to verify org_media template tag library registration.

Provides deterministic proof that Django can discover and load the template tags.
"""

from django.core.management.base import BaseCommand
from django.template.backends.django import get_installed_libraries


class Command(BaseCommand):
    help = 'Verify org_media template tag library is properly registered'

    def handle(self, *args, **options):
        """Verify template tag library registration."""
        self.stdout.write("\n🔍 Verifying org_media template tag library...\n")
        
        # Get all installed template tag libraries
        try:
            libraries = get_installed_libraries()
            
            # Check if org_media is in the list
            if 'org_media' in libraries:
                self.stdout.write(self.style.SUCCESS("✅ org_media is registered"))
                self.stdout.write(f"   Module path: {libraries['org_media']}")
                
                # Try to import the module to verify filters
                try:
                    module_path = libraries['org_media']
                    import importlib
                    module = importlib.import_module(module_path)
                    
                    # Check for the register object and its filters
                    if hasattr(module, 'register'):
                        register = module.register
                        filters_found = []
                        
                        if 'safe_file_url' in register.filters:
                            filters_found.append('safe_file_url')
                        if 'safe_file_exists' in register.filters:
                            filters_found.append('safe_file_exists')
                        
                        if filters_found:
                            self.stdout.write(f"   Filters found: {', '.join(filters_found)}")
                            self.stdout.write("\n✅ Template tag library is working correctly!")
                        else:
                            self.stdout.write(
                                self.style.WARNING("⚠️  No filters found in org_media")
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING("⚠️  org_media has no 'register' object")
                        )
                        
                except Exception as import_error:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Could not import org_media module: {import_error}"
                        )
                    )
                    self.stdout.write("   However, library IS registered with Django")
                
            else:
                self.stdout.write(self.style.ERROR("❌ org_media not found in installed libraries"))
                
                # Show available libraries for debugging
                self.stdout.write("\n📋 Available template tag libraries:")
                for lib_name in sorted(libraries.keys()):
                    self.stdout.write(f"   - {lib_name}")
                
                self.stdout.write(
                    "\n❌ Fix required: Ensure apps.organizations.apps.OrganizationsConfig is in INSTALLED_APPS"
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Unexpected error: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
        
        self.stdout.write(self.style.ERROR("\n❌ Verification failed"))
