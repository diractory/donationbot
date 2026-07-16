import threading
import telegram_api


def schedule_message_deletion(chat_id, message_id, delay_seconds):
    """Deletes a message after `delay_seconds`. Runs in a background thread.

    NOTE: this uses an in-process timer, which is fine for a single Render
    web service instance. If you ever scale to multiple instances/workers,
    replace this with a persisted job (e.g. APScheduler + a DB-backed job
    store, or a Celery/RQ worker) so timers survive process restarts.
    """
    def _delete():
        telegram_api.delete_message(chat_id, message_id)

    timer = threading.Timer(delay_seconds, _delete)
    timer.daemon = True
    timer.start()
