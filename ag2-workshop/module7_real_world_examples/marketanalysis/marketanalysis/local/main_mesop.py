from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="marketanalysis",
)

# start the fastagency app with the following command
# gunicorn marketanalysis.local.main_mesop:app
