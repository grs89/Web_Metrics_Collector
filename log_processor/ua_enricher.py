from user_agents import parse

class UAEnricher:
    GOOD_BOTS = ['googlebot', 'bingbot', 'duckduckbot', 'baiduspider', 'yandexbot', 'facebookexternalhit', 'twitterbot', 'linkedinbot', 'slackbot', 'telegrambot']
    BAD_BOTS = ['mj12bot', 'ahrefsbot', 'semrushbot', 'dotbot', 'petalbot', 'bytespider', 'mauibot', 'megaindex', 'colly', 'go-http-client', 'python-requests']

    def __init__(self):
        pass

    def _classify_bot(self, ua_string):
        ua_lower = ua_string.lower()
        
        for bot in self.BAD_BOTS:
            if bot in ua_lower:
                return 'Bad Bot'
        
        for bot in self.GOOD_BOTS:
            if bot in ua_lower:
                return 'Good Bot'
                
        return 'Unknown Bot'

    def enrich(self, user_agent_string):
        """
        Parses the user agent string and returns a dictionary with
        browser, os, and device information.
        """
        if not user_agent_string or user_agent_string == '-':
            return {
                'browser': 'Unknown',
                'os': 'Unknown',
                'device': 'Unknown'
            }

        try:
            user_agent = parse(user_agent_string)
            
            # Browser
            browser = f"{user_agent.browser.family} {user_agent.browser.version_string}".strip()
            
            # OS
            os_info = f"{user_agent.os.family} {user_agent.os.version_string}".strip()
            
            # Device
            if user_agent.is_mobile:
                device = 'Mobile'
            elif user_agent.is_tablet:
                device = 'Tablet'
            elif user_agent.is_pc:
                device = 'PC'
            elif user_agent.is_bot:
                device = 'Bot'
            else:
                device = 'Other'

            # Bot Category
            bot_category = 'User'
            if user_agent.is_bot:
                bot_category = self._classify_bot(user_agent_string)
            elif 'Bad Bot' == self._classify_bot(user_agent_string): # Double check via bad bot list even if not flagged by library
                 bot_category = 'Bad Bot'
                 device = 'Bot'

            return {
                'browser': browser or 'Unknown',
                'os': os_info or 'Unknown',
                'device': device,
                'bot_category': bot_category
            }
        except Exception:
            return {
                'browser': 'Unknown',
                'os': 'Unknown',
                'device': 'Unknown',
                'bot_category': 'User'
            }
