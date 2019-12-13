from collections import OrderedDict
from dataclasses import dataclass
import pprint
import os
import typing
import yaml

import defect_metrics.logging.logger as logger

YAML = 'yaml'

logging = logger.Logger()


class ConfigFileType:
    def __init__(self, mapping_file: str, pillar: str, order_key: str = 'order'):
        self.file = mapping_file
        self.reserved_section = order_key
        self.mappings = {}
        self.order = []
        self.pillar = pillar
        self.cfg = None

        if not os.path.exists(self.file):
            logging.warn(f"Can't find {self.file}")
        else:
            self.mappings, self.cfg = self.read_config_file()
            self.order = self.get_order()

    def read_config_file(self):
        raise NotImplementedError

    def get_order(self):
        raise NotImplementedError

    def get_sprints(self):
        raise NotImplementedError

    def get_projects(self):
        raise NotImplementedError

    def get_labels(self):
        raise NotImplementedError

    def get_defined_pillars(self):
        raise NotImplementedError

    def get_url(self):
        raise NotImplementedError

    def get_subproducts(self):
        # For products that are comprised of combinations of existing (defined)
        # products. e.g.  = FLIP = [Neutron + DataPlane] * label_filter
        raise NotImplementedError

    def get_reverse_status_mappings(self):
        raise NotImplementedError

    def get_pillar_project_info(self):
        raise NotImplementedError


def get_configuration(mapping_file: str, pillar: str, order_key: str = 'order') -> ConfigFileType:

    args = {'mapping_file': mapping_file,
            'order_key': order_key,
            'pillar': pillar}

    logging.debug(f"Config Args:\n{pprint.pformat(args)}\n")

    return YamlFile(**args)


def get_pillars(mapping_file: str) -> typing.List[str]:
    with open(mapping_file, "r") as FILE:
        cfg = yaml.load(FILE, Loader=yaml.FullLoader)

    return sorted(cfg.keys())


@dataclass
class YamlKeywords:
    STATES: str = 'states'
    SPRINTS: str = 'sprints'
    PROJECTS: str = 'projects'
    PRODUCTS: str = 'products'
    INTERVAL: str = 'sprint_interval'
    LABELS: str = 'labels'
    URL: str = 'url'


class YamlFile(ConfigFileType):

    def read_config_file(self) -> typing.Tuple[dict, dict]:
        mappings = {}

        with open(self.file, "r") as FILE:
            self.cfg = yaml.load(FILE, Loader=yaml.FullLoader)

        for pillar, info_dict in self.cfg.items():
            logging.info(f"Pillar: {pillar}")

            mappings[pillar] = {}
            for state, equiv_list in info_dict[YamlKeywords.STATES].items():
                mappings[pillar].update(dict([(equiv, state) for equiv in equiv_list]))

        return mappings, self.cfg

    def get_defined_pillars(self) -> typing.List[str]:
        return sorted(self.cfg.keys())

    def get_order(self) -> str:
        target = self.cfg[self.pillar]
        return target.get(self.reserved_section, None)

    def get_sprints(self) -> typing.Dict:
        target = self.cfg[self.pillar]
        sprints = target.get(YamlKeywords.SPRINTS, None)
        if sprints is not None:
            data = [(k, v) for k, v in sprints.items()]
            sprints = OrderedDict(sorted(data, key=lambda sprint: sprint[1][0]))
        return sprints

    def get_projects(self) -> typing.List:
        target = self.cfg[self.pillar]
        return target.get(YamlKeywords.PROJECTS, None)

    def get_sprint_interval(self) -> str:
        target = self.cfg[self.pillar]
        return target.get(YamlKeywords.INTERVAL, None)

    def get_labels(self) -> typing.List[str]:
        target = self.cfg[self.pillar]
        return target.get(YamlKeywords.LABELS, None)

    def get_url(self) -> str:
        target = self.cfg[self.pillar]
        return target.get(YamlKeywords.URL, None)

    def get_subproducts(self) -> typing.List[str]:
        target = self.cfg[self.pillar]
        return target.get(YamlKeywords.PRODUCTS, None)

    def get_reverse_status_mappings(self) -> typing.Dict[str, str]:
        states = self.cfg[self.pillar][YamlKeywords.STATES]
        reverse_mappings = dict([(a_s, state) for state, alt_states in states.items() for a_s in alt_states])
        return reverse_mappings

    def get_pillar_project_info(self) -> str:
        output = "\nList of defined Pillars and Jira Projects:\n"
        for pillar in self.get_defined_pillars():
            output += f"\n * {pillar}:\n    - {', '.join(self.cfg[pillar][YamlKeywords.PROJECTS])}\n"
        return output
