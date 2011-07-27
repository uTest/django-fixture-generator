from django.dispatch import Signal


data_dumped = Signal(providing_args=["databases", "models"])
