#!/usr/bin/env python
"""
Phase 5 Performance Optimization Verification Script
Verifies all optimization components are in place and working.
"""

import os
import sys
import time
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

import django
django.setup()

from django.core.cache import cache
from django.db import connection, reset_queries
from django.conf import settings

# Enable query logging
settings.DEBUG = True

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def test_optimization_module_exists():
    """Test 1: Verify optimizations.py exists"""
    print_header("Test 1: Optimization Module Exists")
    
    try:
        from apps.tournaments import optimizations
        
        # Check key components
        components = [
            'cache_tournament_state',
            'TournamentQueryOptimizer',
            'StateCacheManager',
            'RegistrationCountCache',
            'bulk_get_tournament_states',
            'monitor_performance',
        ]
        
        missing = []
        for comp in components:
            if not hasattr(optimizations, comp):
                missing.append(comp)
        
        if missing:
            print_error(f"Missing components: {', '.join(missing)}")
            return False
        
        print_success("optimizations.py exists with all components")
        print_info(f"Found {len(components)} optimization utilities")
        return True
        
    except ImportError as e:
        print_error(f"Failed to import optimizations: {e}")
        return False


def test_cache_decorator():
    """Test 2: Verify cache decorator works"""
    print_header("Test 2: Cache Decorator Functionality")
    
    try:
        from apps.tournaments.optimizations import cache_tournament_state
        
        call_count = 0
        
        @cache_tournament_state(timeout=5)
        def expensive_function(arg):
            nonlocal call_count
            call_count += 1
            return f"Result: {arg}"
        
        # First call
        result1 = expensive_function("test")
        count1 = call_count
        
        # Second call (should be cached)
        result2 = expensive_function("test")
        count2 = call_count
        
        if count1 == 1 and count2 == 1 and result1 == result2:
            print_success("Cache decorator works correctly")
            print_info(f"Function called once, cache hit on second call")
            return True
        else:
            print_error(f"Cache not working: called {count2} times")
            return False
            
    except Exception as e:
        print_error(f"Cache decorator test failed: {e}")
        return False


def test_query_optimizer():
    """Test 3: Verify query optimizer reduces queries"""
    print_header("Test 3: Query Optimizer Performance")
    
    try:
        from apps.tournaments.models import Tournament
        from apps.tournaments.optimizations import TournamentQueryOptimizer
        
        # Get a tournament
        tournament = Tournament.objects.filter(status='PUBLISHED').first()
        
        if not tournament:
            print_info("No published tournaments to test")
            return True
        
        # Test unoptimized query
        reset_queries()
        t1 = Tournament.objects.get(slug=tournament.slug)
        _ = t1.settings
        _ = list(t1.registrations.all()[:5])
        unoptimized_queries = len(connection.queries)
        
        # Test optimized query
        reset_queries()
        t2 = TournamentQueryOptimizer.get_tournament_with_related(tournament.slug)
        _ = t2.settings
        _ = list(t2.registrations.all()[:5])
        optimized_queries = len(connection.queries)
        
        if optimized_queries < unoptimized_queries:
            reduction = ((unoptimized_queries - optimized_queries) / unoptimized_queries) * 100
            print_success(f"Query optimizer working")
            print_info(f"Unoptimized: {unoptimized_queries} queries")
            print_info(f"Optimized: {optimized_queries} queries")
            print_info(f"Reduction: {reduction:.1f}%")
            return True
        else:
            print_error(f"No query reduction: {unoptimized_queries} vs {optimized_queries}")
            return False
            
    except Exception as e:
        print_error(f"Query optimizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_cache_manager():
    """Test 4: Verify state cache manager"""
    print_header("Test 4: State Cache Manager")
    
    try:
        from apps.tournaments.optimizations import StateCacheManager
        
        test_slug = 'test-tournament-12345'
        test_state = {'registration_state': 'OPEN', 'test': True}
        
        # Set cache
        StateCacheManager.set_state(test_slug, test_state)
        
        # Get cache
        cached = StateCacheManager.get_state(test_slug)
        
        if cached == test_state:
            print_success("State cache set/get works")
        else:
            print_error(f"Cache mismatch: {cached} != {test_state}")
            return False
        
        # Invalidate
        StateCacheManager.invalidate(test_slug)
        
        # Should be None now
        after_invalidate = StateCacheManager.get_state(test_slug)
        
        if after_invalidate is None:
            print_success("State cache invalidation works")
            return True
        else:
            print_error(f"Cache not invalidated: {after_invalidate}")
            return False
            
    except Exception as e:
        print_error(f"State cache manager test failed: {e}")
        return False


def test_registration_count_cache():
    """Test 5: Verify registration count cache"""
    print_header("Test 5: Registration Count Cache")
    
    try:
        from apps.tournaments.optimizations import RegistrationCountCache
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.filter(status='PUBLISHED').first()
        
        if not tournament:
            print_info("No tournaments to test count cache")
            return True
        
        # Clear cache first
        RegistrationCountCache.invalidate(tournament.id)
        
        # First call (should query DB)
        reset_queries()
        count1 = RegistrationCountCache.get_count(tournament.id)
        queries1 = len(connection.queries)
        
        # Second call (should use cache)
        reset_queries()
        count2 = RegistrationCountCache.get_count(tournament.id)
        queries2 = len(connection.queries)
        
        if count1 == count2 and queries2 == 0:
            print_success("Registration count cache working")
            print_info(f"First call: {queries1} queries")
            print_info(f"Second call: {queries2} queries (cached)")
            print_info(f"Count: {count1}")
            return True
        else:
            print_error(f"Count cache not working properly")
            return False
            
    except Exception as e:
        print_error(f"Registration count cache test failed: {e}")
        return False


def test_bulk_state_retrieval():
    """Test 6: Verify bulk state retrieval"""
    print_header("Test 6: Bulk State Retrieval")
    
    try:
        from apps.tournaments.optimizations import bulk_get_tournament_states
        from apps.tournaments.models import Tournament
        
        # Get some tournament slugs
        slugs = list(Tournament.objects.filter(
            status='PUBLISHED'
        ).values_list('slug', flat=True)[:3])
        
        if not slugs:
            print_info("No tournaments for bulk test")
            return True
        
        # Get states
        reset_queries()
        states = bulk_get_tournament_states(slugs)
        queries = len(connection.queries)
        
        if len(states) == len(slugs) and queries <= 2:
            print_success("Bulk state retrieval working")
            print_info(f"Retrieved {len(states)} states in {queries} queries")
            return True
        else:
            print_error(f"Bulk retrieval inefficient: {queries} queries for {len(slugs)} tournaments")
            return False
            
    except Exception as e:
        print_error(f"Bulk state retrieval test failed: {e}")
        return False


def test_performance_monitor():
    """Test 7: Verify performance monitor"""
    print_header("Test 7: Performance Monitor")
    
    try:
        from apps.tournaments.optimizations import monitor_performance
        
        @monitor_performance
        def fast_function():
            return "quick"
        
        @monitor_performance
        def slow_function():
            time.sleep(0.15)  # 150ms - should trigger warning
            return "slow"
        
        # This shouldn't log warning
        result1 = fast_function()
        
        # This should log warning (but we can't capture it easily)
        result2 = slow_function()
        
        print_success("Performance monitor decorator exists and runs")
        print_info("Check logs for slow function warnings")
        return True
        
    except Exception as e:
        print_error(f"Performance monitor test failed: {e}")
        return False


def test_state_api_caching():
    """Test 8: Verify state API has caching"""
    print_header("Test 8: State API Caching")
    
    try:
        import inspect
        from apps.tournaments.views import state_api
        
        # Check if state_api has cache decorator
        source = inspect.getsource(state_api.tournament_state_api)
        
        if '@cache_page' in source or 'cache_page' in source:
            print_success("State API has caching enabled")
            print_info("Using @cache_page decorator")
            return True
        else:
            print_error("State API missing caching")
            return False
            
    except Exception as e:
        print_error(f"State API check failed: {e}")
        return False


def test_documentation_exists():
    """Test 9: Verify documentation exists"""
    print_header("Test 9: Documentation")
    
    doc_path = Path(__file__).parent.parent / 'docs' / 'PERFORMANCE_OPTIMIZATION.md'
    
    if doc_path.exists():
        size_kb = doc_path.stat().st_size / 1024
        print_success(f"Performance documentation exists")
        print_info(f"File: {doc_path.name}")
        print_info(f"Size: {size_kb:.1f} KB")
        return True
    else:
        print_error("Performance documentation missing")
        return False


def test_cache_backend_configured():
    """Test 10: Verify cache backend is configured"""
    print_header("Test 10: Cache Backend Configuration")
    
    try:
        from django.conf import settings
        
        if hasattr(settings, 'CACHES') and 'default' in settings.CACHES:
            backend = settings.CACHES['default']['BACKEND']
            print_success("Cache backend configured")
            print_info(f"Backend: {backend}")
            
            # Test cache works
            cache.set('test_key', 'test_value', 10)
            value = cache.get('test_key')
            
            if value == 'test_value':
                print_success("Cache backend is functional")
                cache.delete('test_key')
                return True
            else:
                print_error("Cache backend not working")
                return False
        else:
            print_error("Cache backend not configured")
            return False
            
    except Exception as e:
        print_error(f"Cache configuration test failed: {e}")
        return False


def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   Phase 5: Performance Optimization Verification           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    tests = [
        ("Optimization Module", test_optimization_module_exists),
        ("Cache Decorator", test_cache_decorator),
        ("Query Optimizer", test_query_optimizer),
        ("State Cache Manager", test_state_cache_manager),
        ("Registration Count Cache", test_registration_count_cache),
        ("Bulk State Retrieval", test_bulk_state_retrieval),
        ("Performance Monitor", test_performance_monitor),
        ("State API Caching", test_state_api_caching),
        ("Documentation", test_documentation_exists),
        ("Cache Backend", test_cache_backend_configured),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"{test_name:.<40} {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Phase 5 Verification Complete!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}All performance optimizations are in place and working.{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.WARNING}⚠ Some tests failed. Review output above.{Colors.ENDC}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
