from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="myappaws",
)

# start the fastagency app with the following command
# gunicorn myappaws.local.main_mesop:app
