import logging

class BotVerifier:
    @staticmethod
    def is_fake_googlebot(user_agent, hostname):
        """
        Verifies if a user agent claiming to be Googlebot is legitimate
        by checking the reverse DNS hostname.
        """
        if not user_agent:
            return False
            
        user_agent = user_agent.lower()
        if 'googlebot' in user_agent:
            if not hostname or not (hostname.endswith('.googlebot.com') or hostname.endswith('.google.com')):
                return True # It IS a fake bot
        
        return False
