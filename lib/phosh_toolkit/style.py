"""Light or dark: follow the system, or the user's choice in the app's
preferences (phosh-toolkit docs/decisions/app-accent-colours.md)."""
from gi.repository import Adw, Gtk

# Stored value, label, and the AdwColorScheme it selects.
STYLES = (
    ("system", "Follow System", "DEFAULT"),
    ("light", "Light", "FORCE_LIGHT"),
    ("dark", "Dark", "FORCE_DARK"),
)


def color_scheme(style):
    """The AdwColorScheme member name for a stored style."""
    for value, _, scheme in STYLES:
        if value == style:
            return scheme
    return "DEFAULT"


def apply(style):
    Adw.StyleManager.get_default().set_color_scheme(
        getattr(Adw.ColorScheme, color_scheme(style)))


def style_row(current, changed):
    """An "Appearance → Style" combo row showing `current`; choosing an
    entry applies it and calls changed(style) so the app can keep it."""
    values = [value for value, _, _ in STYLES]
    row = Adw.ComboRow(title="Style", model=Gtk.StringList.new(
        [label for _, label, _ in STYLES]))
    row.set_selected(values.index(current) if current in values else 0)

    def on_selected(*_):
        style = values[row.get_selected()]
        apply(style)
        changed(style)

    row.connect("notify::selected", on_selected)
    return row
