class StateManager:
    def __init__(self):
        self.states = {}

    def set_state(self, user_id, state, data=None):
        self.states[user_id] = {'state': state, 'data': data or {}}

    def get_state(self, user_id):
        return self.states.get(user_id, {'state': None, 'data': {}})

    def clear_state(self, user_id):
        if user_id in self.states:
            del self.states[user_id]

# Global state manager instance
state_manager = StateManager()