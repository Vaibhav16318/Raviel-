import datetime
import difflib
import json
import os
import re
import subprocess
import webbrowser

from google import genai


class RAVIELAgent:
    """
    RAVIEL desktop AI agent.

    Routes requests between:
    - fast local commands
    - Windows application control
    - websites
    - time/date
    - weather
    - document/RAG questions
    - general local AI

    Designed for Windows + Ollama.
    """

    def __init__(
        self,
        rag_service,
        model: str = "qwen2.5:0.5b-instruct",
    ):
        self.rag_service = rag_service
        self.model = model

        # Keep the Ollama model permanently warm.
        # This avoids repeated model loading between requests.
        self.keep_alive = -1

        # Cache Windows Start Apps so every "open ..."
        # command does not have to start PowerShell again.
        self.windows_apps = self._load_windows_apps()

    # ============================================================
    # MAIN ENTRY POINT
    # ============================================================

    def ask(
        self,
        query: str,
        voice_mode: bool = False,
    ) -> str:
        """
        Main RAVIEL entry point.

        voice_mode=True:
            Optimizes general AI responses for spoken interaction.

        voice_mode=False:
            Normal desktop/text behavior.

        Explicit requests for detailed answers override the
        short-answer voice optimization.
        """

        query = query.strip()

        if not query:
            return "I'm listening."

        lower = self._normalize(query)

        # --------------------------------------------------------
        # OPEN / LAUNCH / START
        # --------------------------------------------------------

        if self._is_open_command(lower):
            return self._handle_open_command(query)

        # --------------------------------------------------------
        # CLOSE / EXIT / QUIT
        # --------------------------------------------------------

        if self._is_close_command(lower):
            return self._handle_close_command(query)

        # --------------------------------------------------------
        # TIME
        # --------------------------------------------------------

        if self._contains_any(
            lower,
            [
                "what time is it",
                "what's the time",
                "what is the time",
                "current time",
                "tell me the time",
                "time right now",
                "what time right now",
                "समय क्या है",
                "अभी कितने बजे हैं",
                "कितने बजे हैं",
            ],
        ):
            now = datetime.datetime.now()

            return (
                f"It is "
                f"{now.strftime('%I:%M %p').lstrip('0')}."
            )

        # --------------------------------------------------------
        # DATE
        # --------------------------------------------------------

        if self._contains_any(
            lower,
            [
                "what date is it",
                "today's date",
                "what is today's date",
                "current date",
                "what day is it",
                "what is today",
                "आज की तारीख",
                "आज कौन सा दिन है",
            ],
        ):
            now = datetime.datetime.now()

            return (
                f"Today is "
                f"{now.strftime('%A, %B %d, %Y')}."
            )

        # --------------------------------------------------------
        # WEATHER
        # --------------------------------------------------------

        if self._contains_any(
            lower,
            [
                "weather",
                "temperature outside",
                "temperature today",
                "is it raining",
                "will it rain",
                "forecast",
                "how's the weather",
                "how is the weather",
                "मौसम",
                "आज का मौसम",
                "बारिश",
                "तापमान",
            ],
        ):
            return self._get_weather()

        # --------------------------------------------------------
        # DOCUMENT / RAG
        # --------------------------------------------------------

        if self._looks_like_document_question(lower):
            try:
                result = self.rag_service.ask(query)

                if result and getattr(result, "success", False):
                    answer = getattr(
                        result,
                        "answer",
                        "",
                    )

                    if answer and answer.strip():
                        return answer.strip()

            except Exception as exc:
                print(f"RAG error: {exc}")

            # If document answering fails, continue to
            # general AI rather than making RAVIEL appear broken.

        # --------------------------------------------------------
        # GENERAL AI
        # --------------------------------------------------------

        return self._general_ai(
            query,
            voice_mode=voice_mode,
        )

    # ============================================================
    # NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize speech-transcribed commands.
        """

        text = text.lower().strip()

        # Remove common punctuation from the end.
        text = re.sub(
            r"[?!.,]+$",
            "",
            text,
        )

        # Collapse repeated whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # ============================================================
    # COMMAND DETECTION
    # ============================================================

    @staticmethod
    def _is_open_command(query: str) -> bool:
        prefixes = (
            "open ",
            "launch ",
            "start ",
            "run ",
            "खोलो ",
            "ओपन ",
            "चलाओ ",
            "चला दो ",
        )

        return query.startswith(prefixes)

    @staticmethod
    def _is_close_command(query: str) -> bool:
        prefixes = (
            "close ",
            "exit ",
            "quit ",
            "stop ",
            "बंद करो ",
            "बंद ",
            "क्लोज ",
        )

        return query.startswith(prefixes)

    # ============================================================
    # GENERAL AI
    # ============================================================

    @staticmethod
    def _wants_detailed_answer(query: str) -> bool:
        """
        Detect whether the user explicitly asks for a detailed
        or long-form answer.

        This allows voice mode to remain fast for normal questions
        while still supporting long answers when requested.
        """

        text = query.lower().strip()

        detail_phrases = (
            # English
            "explain in detail",
            "explain this in detail",
            "explain thoroughly",
            "explain deeply",
            "give me details",
            "give me more details",
            "give me a detailed explanation",
            "give me a detailed answer",
            "give me a long answer",
            "give me a full explanation",
            "give me the full explanation",
            "tell me everything",
            "in detail",
            "in depth",
            "deep dive",
            "detailed explanation",
            "detailed answer",
            "long answer",
            "thorough explanation",
            "elaborate",
            "go into detail",
            "explain everything",

            # Hindi
            "विस्तार से बताओ",
            "विस्तार से समझाओ",
            "पूरी जानकारी दो",
            "डिटेल में बताओ",
            "विस्तार में बताओ",
            "विस्तार से समझाइए",
            "पूरी जानकारी चाहिए",
            "सब कुछ बताओ",
        )

        return any(
            phrase in text
            for phrase in detail_phrases
        )

    def _general_ai(
        self,
        query: str,
        voice_mode: bool = False,
    ) -> str:
        """
        General-purpose local AI.

        Voice mode:
            Optimized for low latency and natural spoken answers.

        Text mode:
            Allows more detailed responses.

        Explicit requests for detail override the short-answer
        voice optimization.
        """

        wants_detail = self._wants_detailed_answer(query)

        # --------------------------------------------------------
        # Decide response length.
        # --------------------------------------------------------

        if voice_mode and not wants_detail:
            response_instruction = """
- This is a voice conversation.
- Give the direct answer immediately.
- Normally answer in 1–3 short spoken sentences.
- Prefer roughly 20–50 words.
- Do not add unnecessary background.
- Do not repeat the question.
- Avoid filler.
"""
            max_tokens = 64

        elif wants_detail:
            response_instruction = """
- The user explicitly wants a detailed explanation.
- Give a complete and useful answer.
- You may use multiple paragraphs or bullet points when helpful.
- Explain the important reasoning and details.
- Do not artificially shorten the answer.
"""
            max_tokens = 180

        else:
            response_instruction = """
- Give a useful direct answer.
- Use as much detail as the question requires.
- Do not unnecessarily repeat information.
- If the user asks for a detailed explanation, provide one.
"""
            max_tokens = 160

        # --------------------------------------------------------
        # System prompt
        # --------------------------------------------------------

        system_prompt = f"""
You are RAVIEL, a fast local desktop AI assistant.

You are speaking with the user naturally.

LANGUAGE:
- Respond in the same language as the user.
- English → English.
- Hindi → Hindi.
- Hinglish → natural Hinglish.
- Bhojpuri → Bhojpuri when possible.
- Haryanavi → Haryanavi when possible.
- Do not translate the user's language into English unnecessarily.
- Preserve the user's language throughout the answer.
- If the user mixes Hindi and English, naturally mix Hindi and English.

RESPONSE LENGTH:
{response_instruction}

STYLE:
- Sound intelligent, friendly, natural and confident.
- Speak naturally rather than like an encyclopedia.
- Use simple language unless the user asks for technical detail.
- Give the answer first.
- Avoid filler such as:
  "Sure!"
  "Of course!"
  "I'd be happy to help!"
  unless it genuinely improves the conversation.

IMPORTANT:
- Do not mention RAG, retrieval, context, embeddings, vector stores,
  models, or internal implementation unless the user specifically asks.
- Do not claim to have performed a computer action unless RAVIEL
  actually performed it through a command handler.
- Answer normal general-knowledge questions directly.
- Do not invent facts when you are uncertain.
"""

        try:
            api_key = os.environ.get("GEMINI_API_KEY")

            if not api_key:
                print("RAVIEL Gemini error: GEMINI_API_KEY is not configured.")
                return "The AI service is not configured right now."

            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=query,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    max_output_tokens=max_tokens,
                ),
            )

            answer = (response.text or "").strip()

            if not answer:
                return "I don't have an answer for that."

            return answer

        except Exception as exc:
            print(f"RAVIEL Gemini error: {exc}")
            return "I couldn't process that request right now."

    # ============================================================
    # DOCUMENT ROUTING
    # ============================================================

    def _looks_like_document_question(
        self,
        query: str,
    ) -> bool:
        """
        Only send explicitly document-related questions through RAG.

        General questions stay on the fast local AI path.
        """

        document_terms = [
            "according to the document",
            "according to the documents",
            "according to the file",
            "according to the files",
            "in the document",
            "in the documents",
            "in the file",
            "in the files",
            "from the document",
            "from the documents",
            "from the file",
            "from the files",
            "uploaded document",
            "uploaded file",
            "provided document",
            "provided file",
            "what does the document say",
            "what do the documents say",
            "summarize the document",
            "summarize the documents",
            "summarize the file",
            "summarize the files",
            "based on the document",
            "based on the documents",
            "based on the file",
            "based on the files",
        ]

        return any(
            term in query
            for term in document_terms
        )

    # ============================================================
    # WINDOWS START APPS
    # ============================================================

    def _load_windows_apps(self):
        """
        Read installed Windows Start Menu applications.

        Uses:
            Get-StartApps
        """

        try:
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Get-StartApps | "
                    "Select-Object Name,AppID | "
                    "ConvertTo-Json -Compress"
                ),
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )

            if result.returncode != 0:
                print(
                    "Could not read Windows Start Apps:",
                    result.stderr,
                )
                return []

            raw = result.stdout.strip()

            if not raw:
                return []

            data = json.loads(raw)

            if isinstance(data, dict):
                data = [data]

            apps = []

            for item in data:
                name = str(
                    item.get("Name", "")
                ).strip()

                app_id = str(
                    item.get("AppID", "")
                ).strip()

                if name and app_id:
                    apps.append(
                        {
                            "name": name,
                            "app_id": app_id,
                        }
                    )

            print(
                f"RAVIEL loaded {len(apps)} Windows apps."
            )

            return apps

        except Exception as exc:
            print(
                f"Windows app discovery error: {exc}"
            )

            return []

    # ============================================================
    # OPEN APPLICATIONS
    # ============================================================

    def _handle_open_command(
        self,
        query: str,
    ) -> str:
        """
        Open Windows applications dynamically.

        RAVIEL first checks special websites/aliases,
        then searches the real Windows Start Apps list.
        """

        target = self._normalize(query)

        # Remove command words.
        target = re.sub(
            r"^(open|launch|start|run)\s+",
            "",
            target,
        )

        target = re.sub(
            r"^(खोलो|ओपन|चलाओ|चला दो)\s+",
            "",
            target,
        )

        target = target.strip()

        if not target:
            return "What would you like me to open?"

        # --------------------------------------------------------
        # Website aliases
        # --------------------------------------------------------

        websites = {
             "gmail": "https://mail.google.com",
             "google mail": "https://mail.google.com",

             "youtube": "https://www.youtube.com",

             "github": "https://github.com",

             "chatgpt": "https://chatgpt.com",

             "linkedin": "https://www.linkedin.com",
             "linkedin web": "https://www.linkedin.com",
             "linkedin website": "https://www.linkedin.com",

             "whatsapp": "https://web.whatsapp.com",
             "whatsapp web": "https://web.whatsapp.com",

             "notion": "https://www.notion.so",
             "notion web": "https://www.notion.so",

             "google": "https://www.google.com",
             "google search": "https://www.google.com",

             "facebook": "https://www.facebook.com",

             "instagram": "https://www.instagram.com",

             "twitter": "https://x.com",
             "x": "https://x.com",
        }

        # Exact website aliases first.
        if target in websites:
            try:
                webbrowser.open(
                    websites[target]
                )

                return f"Opening {target}."

            except Exception as exc:
                print(
                    f"Website open error: {exc}"
                )

                return (
                    f"I couldn't open {target}."
                )

        # --------------------------------------------------------
        # Common application aliases
        # --------------------------------------------------------

        aliases = {
            "chrome": [
                "google chrome",
                "chrome",
            ],
            "google chrome": [
                "google chrome",
                "chrome",
            ],
            "brave": [
                "brave",
            ],
            "linkedin": [
                "linkedin",
            ],
            "whatsapp": [
                "whatsapp",
            ],
            "vs code": [
                "visual studio code",
                "vs code",
            ],
            "visual studio code": [
                "visual studio code",
                "vs code",
            ],
            "code": [
                "visual studio code",
            ],
            "cursor": [
                "cursor",
            ],
            "discord": [
                "discord",
            ],
            "zoom": [
                "zoom workplace",
                "zoom",
            ],
            "excel": [
                "excel",
            ],
            "word": [
                "word",
            ],
            "powerpoint": [
                "powerpoint",
            ],
            "power point": [
                "powerpoint",
            ],
            "outlook": [
                "outlook",
            ],
            "notepad": [
                "notepad",
            ],
            "calculator": [
                "calculator",
            ],
            "calc": [
                "calculator",
            ],
            "paint": [
                "paint",
            ],
            "file explorer": [
                "file explorer",
            ],
            "explorer": [
                "file explorer",
            ],
            "task manager": [
                "task manager",
            ],
            "settings": [
                "settings",
            ],
            "obsidian": [
                "obsidian",
            ],
            "notion": [
                "notion",
            ],
            "teams": [
                "microsoft teams",
                "teams",
            ],
            "onedrive": [
                "onedrive",
            ],
            "onenote": [
                "onenote",
            ],
            "power automate": [
                "power automate",
            ],
        }

        # --------------------------------------------------------
        # Convert aliases into search terms.
        # --------------------------------------------------------

        search_terms = [target]

        if target in aliases:
            search_terms.extend(
                aliases[target]
            )

        # Also remove common words.
        simplified = re.sub(
            r"\b(app|application|program|browser)\b",
            "",
            target,
        ).strip()

        if simplified:
            search_terms.append(
                simplified
            )

        # --------------------------------------------------------
        # Exact / close Windows app matching
        # --------------------------------------------------------

        app = self._find_windows_app(
            search_terms
        )

        if app:
            return self._launch_windows_app(
                app
            )

        # --------------------------------------------------------
        # Special built-in Windows programs
        # --------------------------------------------------------

        builtins = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "command prompt": "cmd.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "file explorer": "explorer.exe",
            "explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "settings": "ms-settings:",
        }

        if target in builtins:
            command = builtins[target]

            try:
                if command.endswith(":"):
                    os.startfile(command)
                else:
                    subprocess.Popen(
                        command,
                        shell=False,
                    )

                return f"Opening {target}."

            except Exception as exc:
                print(
                    f"Built-in launch error: {exc}"
                )

                return (
                    f"I couldn't open {target}."
                )

        # --------------------------------------------------------
        # If it looks like a website, open it.
        # --------------------------------------------------------

        if (
            target.startswith("http://")
            or target.startswith("https://")
        ):
            try:
                webbrowser.open(target)

                return "Opening it."

            except Exception:
                return (
                    "I couldn't open that website."
                )

        # --------------------------------------------------------
        # Friendly fallback
        # --------------------------------------------------------

        return (
            f"I couldn't find an installed app called "
            f"{target}."
        )

    # ============================================================
    # FIND WINDOWS APP
    # ============================================================

    def _find_windows_app(
        self,
        search_terms,
    ):
        """
        Find the best matching installed Windows app.

        Matching order:
        1. exact
        2. starts-with
        3. contains
        4. fuzzy similarity
        """

        if not self.windows_apps:
            return None

        normalized_apps = []

        for app in self.windows_apps:
            name = self._normalize(
                app["name"]
            )

            normalized_apps.append(
                (
                    name,
                    app,
                )
            )

        # --------------------------------------------------------
        # Exact match
        # --------------------------------------------------------

        for term in search_terms:
            term = self._normalize(term)

            for name, app in normalized_apps:
                if name == term:
                    return app

        # --------------------------------------------------------
        # Starts-with match
        # --------------------------------------------------------

        for term in search_terms:
            term = self._normalize(term)

            candidates = [
                app
                for name, app in normalized_apps
                if name.startswith(term)
            ]

            if candidates:
                return min(
                    candidates,
                    key=lambda item: len(
                        item["name"]
                    ),
                )

        # --------------------------------------------------------
        # Contains match
        # --------------------------------------------------------

        for term in search_terms:
            term = self._normalize(term)

            candidates = [
                app
                for name, app in normalized_apps
                if term in name
            ]

            if candidates:
                return min(
                    candidates,
                    key=lambda item: len(
                        item["name"]
                    ),
                )

        # --------------------------------------------------------
        # Fuzzy match
        # --------------------------------------------------------

        for term in search_terms:
            term = self._normalize(term)

            if len(term) < 3:
                continue

            names = [
                name
                for name, _ in normalized_apps
            ]

            matches = difflib.get_close_matches(
                term,
                names,
                n=1,
                cutoff=0.72,
            )

            if matches:
                best_name = matches[0]

                for name, app in normalized_apps:
                    if name == best_name:
                        return app

        return None

    # ============================================================
    # LAUNCH WINDOWS APP
    # ============================================================

    def _launch_windows_app(
        self,
        app,
    ) -> str:
        """
        Launch a Windows Start App through its AppID.
        """

        name = app["name"]
        app_id = app["app_id"]

        try:
            # Windows AppsFolder launch mechanism.
            subprocess.Popen(
                [
                    "explorer.exe",
                    f"shell:AppsFolder\\{app_id}",
                ],
                shell=False,
            )

            return f"Opening {name}."

        except Exception as exc:
            print(
                f"Windows app launch error for "
                f"{name}: {exc}"
            )

            # Try os.startfile as fallback.
            try:
                os.startfile(
                    f"shell:AppsFolder\\{app_id}"
                )

                return f"Opening {name}."

            except Exception as fallback_exc:
                print(
                    "Fallback launch failed:",
                    fallback_exc,
                )

        return (
            f"I found {name}, but Windows "
            f"couldn't launch it."
        )

    # ============================================================
    # CLOSE APPLICATIONS
    # ============================================================

    def _handle_close_command(
        self,
        query: str,
    ) -> str:
        """
        Safely closes selected applications.

        This intentionally uses a whitelist.
        """

        target = self._normalize(query)

        target = re.sub(
            r"^(close|exit|quit|stop)\s+",
            "",
            target,
        )

        target = re.sub(
            r"^(बंद करो|बंद|क्लोज)\s+",
            "",
            target,
        )

        target = target.strip()

        processes = {
            "notepad": [
                "notepad.exe",
            ],
            "calculator": [
                "CalculatorApp.exe",
                "ApplicationFrameHost.exe",
            ],
            "calc": [
                "CalculatorApp.exe",
                "ApplicationFrameHost.exe",
            ],
            "paint": [
                "mspaint.exe",
            ],
            "whatsapp": [
                "WhatsApp.exe",
            ],
            "chrome": [
                "chrome.exe",
            ],
            "google chrome": [
                "chrome.exe",
            ],
            "brave": [
                "brave.exe",
            ],
            "discord": [
                "Discord.exe",
            ],
            "outlook": [
                "OUTLOOK.EXE",
            ],
            "teams": [
                "ms-teams.exe",
                "Teams.exe",
            ],
            "zoom": [
                "Zoom.exe",
            ],
            "obsidian": [
                "Obsidian.exe",
            ],
            "notion": [
                "Notion.exe",
            ],
            "cursor": [
                "Cursor.exe",
            ],
            "code": [
                "Code.exe",
            ],
            "visual studio code": [
                "Code.exe",
            ],
        }

        # Direct process mapping.
        if target in processes:
            for process in processes[target]:
                self._kill_process(
                    process
                )

            return f"Closing {target}."

        # Try matching installed app name.
        app = self._find_windows_app(
            [target]
        )

        if app:
            process_name = self._guess_process_name(
                app["name"]
            )

            if process_name:
                self._kill_process(
                    process_name
                )

                return (
                    f"Closing {app['name']}."
                )

        return (
            f"I don't have a safe close action "
            f"configured for {target}."
        )

    # ============================================================
    # PROCESS HELPERS
    # ============================================================

    @staticmethod
    def _kill_process(
        process_name: str,
    ):
        try:
            subprocess.run(
                [
                    "taskkill",
                    "/IM",
                    process_name,
                    "/F",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )

        except Exception as exc:
            print(
                f"Process close error: {exc}"
            )

    @staticmethod
    def _guess_process_name(
        app_name: str,
    ):
        """
        Best-effort mapping for common applications.

        Closing arbitrary executables is intentionally avoided.
        """

        mappings = {
            "google chrome": "chrome.exe",
            "brave": "brave.exe",
            "whatsapp": "WhatsApp.exe",
            "discord": "Discord.exe",
            "zoom workplace": "Zoom.exe",
            "cursor": "Cursor.exe",
            "visual studio code": "Code.exe",
            "obsidian": "Obsidian.exe",
            "notion": "Notion.exe",
            "outlook": "OUTLOOK.EXE",
        }

        return mappings.get(
            app_name.lower()
        )

    # ============================================================
    # WEATHER
    # ============================================================

    def _get_weather(self) -> str:
        """
        Lightweight weather lookup.

        Uses wttr.in and requires no API key.
        """

        try:
            import requests

            response = requests.get(
                "https://wttr.in/?format=3",
                timeout=3,
            )

            if response.ok:
                return response.text.strip()

        except Exception as exc:
            print(
                f"Weather lookup error: {exc}"
            )

        return (
            "I couldn't retrieve the weather right now."
        )

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _contains_any(
        text: str,
        phrases: list[str],
    ) -> bool:
        return any(
            phrase in text
            for phrase in phrases
        )
