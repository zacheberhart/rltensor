import numpy as np
from collections import namedtuple

from .core import BaseMemory, RingBuffer
from .utils import sample_batch_indexes


TSExperience = namedtuple('TSExperience',
                          'state, action, reward, terminal')


class TSMemory(BaseMemory):
    def __init__(self, limit, window_length, beta=0.1, *args, **kwargs):
        super(TSMemory, self).__init__(window_length=window_length)
        self.limit = limit
        # Do not use deque to implement the memory. This data structure
        # may seem convenient but
        # it is way too slow on random access. Instead, we use our own
        # ring buffer implementation.
        self.actions = RingBuffer(limit)
        self.rewards = RingBuffer(limit)
        self.terminals = RingBuffer(limit)
        self.observations = RingBuffer(limit)
        self.beta = beta
        self.hist_count = 0

    def sample(self, batch_size, *args, **kwargs):
        num_options = self.nb_entries - (batch_size + self.window_length - 2)
        assert num_options > 0
        idx = np.random.geometric(self.beta) % num_options
        init_idx = self.start_idx - idx
        batch_idxs = np.arange(init_idx - batch_size + 1, init_idx + 1) % self.limit
        # Create experiences
        experiences = []
        # Each idx is index for state1
        for i, idx in enumerate(batch_idxs):
            # Observatio and terminal happens at the same time, so
            # previous index has to keep terminal==False.
            action = self.actions[idx]
            reward = self.rewards[idx]
            terminal = self.terminals[idx]
            state = [self.observations[obs_i] for obs_i in range(idx - self.window_length + 1, idx + 1)]
            scale = state[-1][0]
            state = state / scale
            experiences.append(TSExperience(state=state, action=action,
                                            reward=reward, terminal=terminal))
        assert len(experiences) == batch_size
        return experiences

    def append(self, observation, action, reward, terminal, info, is_store=True):
        super(TSMemory, self).append(observation, action, reward, terminal, info)
        # This needs to be understood as follows: in `observation`,
        # take `action`, obtain `reward`
        # and weather the next state is `terminal` or not.
        if is_store:
            self.observations.append(observation)
            self.actions.append(action)
            self.rewards.append(info["returns"])
            self.terminals.append(terminal)
            self.hist_count += 1

    def _sample_batch_indexes(self, low, high, size, weights=None):
        return sample_batch_indexes(low, high, size, weights)

    @property
    def nb_entries(self):
        return len(self.observations)

    @property
    def start_idx(self):
        return self.hist_count - 1
