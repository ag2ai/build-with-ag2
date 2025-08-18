from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="my_app_azure",
)

# start the fastagency app with the following command
# gunicorn my_app_azure.local.main_mesop:app
