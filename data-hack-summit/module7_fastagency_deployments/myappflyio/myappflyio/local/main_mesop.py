from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="myappflyio",
)

# start the fastagency app with the following command
# gunicorn myappflyio.local.main_mesop:app
