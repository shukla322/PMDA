import asyncio
from pathlib import Path
import sys
import tempfile
import unittest
from pmda.mcp_client import session,call


class ProtocolTests(unittest.TestCase):
    def test_real_stdio_discovery_errors_and_reconnect(self):
        root=Path(__file__).resolve().parents[1]
        (root / "runtime/test-tmp").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root / "runtime/test-tmp") as directory:
            async def exercise():
                # New client sessions represent a server restart/reconnect boundary.
                for attempt in range(2):
                    async with session(sys.executable,root / "tests/fake_mcp.py",directory,Path(directory) / f"stderr-{attempt}.log") as client:
                        listing=await client.list_tools()
                        self.assertEqual({t.name for t in listing.tools},{"fixture_success","fixture_failure"})
                        self.assertEqual((await call(client,"fixture_success",{"value":7}))["value"],7)
                        with self.assertRaises(RuntimeError):
                            await call(client,"fixture_failure",{})
            asyncio.run(exercise())
