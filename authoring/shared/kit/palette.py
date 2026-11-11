"""Named colours for a batch. Painters ask for roles, never literal hex."""
import json
from pathlib import Path

from .draw import mix, rgba


class Palette:
    def __init__(self, colours, origin='<memory>'):
        self.colours, self.origin = dict(colours), origin

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(data['colours'], str(path))

    def __call__(self, name, alpha=1.0):
        """Resolve a role name, a literal '#rrggbb', or a role with a tone shift such as 'coat*0.8'."""
        if not isinstance(name, str):
            return rgba(name, alpha)
        if name.startswith('#'):
            return rgba(name, alpha)
        if '*' in name:
            role, factor = name.split('*')
            return self.tone(role, float(factor), alpha)
        if name not in self.colours:
            raise KeyError(f'{self.origin}: palette has no colour {name!r}')
        return rgba(self.colours[name], alpha)

    def tone(self, name, factor, alpha=1.0):
        """Darken (<1) toward ink or lighten (>1) toward paper, keeping the family warm."""
        base = self(name)
        target = self('ink') if factor < 1 else self('paper')
        amount = (1 - factor) if factor < 1 else min(1.0, factor - 1)
        r, g, b, _ = mix(base, target, amount)
        return (r, g, b, alpha)

    def has(self, name):
        return name in self.colours
