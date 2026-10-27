"""Supervisor lifecycle tests, no Django or external services."""
import subprocess
import unittest
from unittest.mock import Mock, patch
from scripts.render_processes import supervise


class SupervisorTests(unittest.TestCase):
    @patch('scripts.render_processes.signal.signal')
    @patch('scripts.render_processes.os.killpg', create=True)
    def test_child_failure_stops_both_groups(self, killpg, signals):
        worker = Mock(pid=101)
        worker.poll.return_value = 1
        web = Mock(pid=102)
        spawn = Mock(side_effect=[worker, web])
        self.assertEqual(supervise(['daphne', 'test:app'], popen=spawn), 1)
        self.assertEqual({c.args[0] for c in killpg.call_args_list}, {101, 102})
        self.assertEqual(spawn.call_args_list[0].kwargs['env']['DISABLE_INPROCESS_MATCH_REMINDER'], '1')
        command = spawn.call_args_list[0].args[0]
        self.assertIn('--pool=prefork', command)
        self.assertIn('--concurrency=1', command)

    @patch('scripts.render_processes.signal.signal')
    @patch('scripts.render_processes.os.killpg', create=True)
    def test_partial_startup_failure_cleans_worker(self, killpg, signals):
        worker = Mock(pid=101)
        with self.assertRaises(OSError):
            supervise(['daphne'], popen=Mock(side_effect=[worker, OSError('synthetic')]))
        killpg.assert_called_once()
        worker.wait.assert_called_once()

    @patch('scripts.render_processes.signal.signal')
    @patch('scripts.render_processes.os.killpg', create=True)
    @patch('scripts.render_processes.signal.SIGKILL', 9, create=True)
    def test_stuck_shutdown_is_killed(self, killpg, signals):
        import signal
        worker = Mock(pid=101)
        worker.poll.return_value = 1
        worker.wait.side_effect = [subprocess.TimeoutExpired('worker', 25), 0]
        web = Mock(pid=102)
        supervise(['daphne'], popen=Mock(side_effect=[worker, web]))
        self.assertTrue(any(c.args == (101, signal.SIGKILL) for c in killpg.call_args_list))
