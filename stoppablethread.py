import threading


class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        self._thread_pool =  kwargs.pop('pool')
        super(StoppableThread, self).__init__(*args, **kwargs)
        if self._thread_pool is None:
            raise ValueError('Closing pool must be specified!')
        self._thread_pool.append(self)
        self._stop_event = threading.Event()

    @property
    def pool(self):
        return self._thread_pool
    
    def join(self, timeout=None):
        self._stop_event.set()
        self._thread_pool.remove(self)
        super().join(timeout)