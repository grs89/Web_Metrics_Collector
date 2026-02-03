from user_agents import parse

class UAEnricher:
    def __init__(self):
        pass

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

            return {
                'browser': browser or 'Unknown',
                'os': os_info or 'Unknown',
                'device': device
            }
        except Exception:
            return {
                'browser': 'Unknown',
                'os': 'Unknown',
                'device': 'Unknown'
            }
