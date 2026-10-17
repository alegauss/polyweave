from polyweave.kernel.codes import Code

AREAS = {"tone": "a tone made from a declaration"}

CODES = {
    "tone.bad-pitch": Code(
        means="the pitch is outside what a person hears",
        when="a declaration or a search asks for a tone below 20 Hz or above 20 kHz",
        doors=("declare a pitch between 20 and 20000",),
    ),
}
