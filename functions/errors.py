# Block of twitter-check errors
class UserNotFoundError(Exception):
    pass

class RetweetNotFoundError(Exception):
    pass

class DoesNotFollowError(Exception):
    pass

class PostNotFoundError(Exception):
    pass

class RateLimitError(Exception):
    pass