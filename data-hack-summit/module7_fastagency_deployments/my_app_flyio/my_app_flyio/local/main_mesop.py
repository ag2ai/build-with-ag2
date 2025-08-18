from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="my_app_flyio",
)

# start the fastagency app with the following command
# gunicorn my_app_flyio.local.main_mesop:app
