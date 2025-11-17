import anyio
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    # Paste the path returned by `where claude`
    cli_path=r"C:\Users\kerry\.local\bin\claude.exe"   # or ...\AppData\Roaming\npm\claude.cmd
)

async def main():
    async for msg in query(prompt="Say hello from Windows", options=options):
        print(msg)

anyio.run(main)
