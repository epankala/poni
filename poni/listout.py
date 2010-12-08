"""
List output formatting

TODO: messy, rewrite

Copyright (c) 2010 Mika Eloranta
See LICENSE for details.

"""

import sys
from . import colors
from . import core
from . import util


class ListOutput(colors.Output):
    def __init__(self, tool, confman, show_nodes=False, show_systems=False,
                 show_config=False, show_tree=False, show_inherits=False,
                 pattern=False, full_match=False, show_node_prop=False,
                 show_cloud_prop=False, show_config_prop=False,
                 list_props=False,
                 query_status=False, show_settings=False, **kwargs):
        colors.Output.__init__(self, sys.stdout)
        self.show_nodes = show_nodes
        self.show_systems = show_systems
        self.show_config = show_config
        self.show_tree = show_tree
        self.show_inherits = show_inherits
        self.show_node_prop = show_node_prop
        self.show_cloud_prop = show_cloud_prop
        self.show_config_prop = show_config_prop
        self.show_settings = show_settings
        self.list_props = list_props
        self.query_status = query_status
        self.pattern = pattern
        self.full_match = full_match
        self.tool = tool
        self.confman = confman
        self.hindent = 4 * " "
        self.indent = int(show_tree) * self.hindent
        self.formatters = {
            "node": self.format_node,
            "system": self.format_system,
            "config": self.format_config,
            "prop": self.format_prop,
            "cloud": self.format_prop,
            "confprop": self.format_prop,
            "status": self.format_status,
            "setting": self.format_setting,
            }

    def value_repr(self, value, top_level=False):
        if isinstance(value, unicode):
            try:
                value = repr(value.encode("ascii"))
            except UnicodeEncodeError:
                pass

        if isinstance(value, dict):
            if not value:
                yield "none", "gray"
                raise StopIteration()

            if not top_level:
                yield "{", None

            for i, (key, value) in enumerate(value.iteritems()):
                if i > 0:
                    yield ", ", None

                yield key, "key"
                yield ":", None

                for output in self.value_repr(value):
                    yield output

            if not top_level:
                yield "}", None
        elif isinstance(value, str):
            yield value, "str"
        elif isinstance(value, bool):
            yield str(value), "bool"
        elif isinstance(value, (int, long)):
            yield str(value), "int"
        else:
            yield repr(value), "red"

    def format_setting(self, entry):
        yield entry["setting"], "setting"
        yield " = ", None
        for output in self.value_repr(entry["value"]):
            yield output

    def format_status(self, entry):
        yield entry["status"], "status"

    def format_prop(self, entry):
        return self.value_repr(entry["prop"], top_level=True)

    def format_system(self, entry):
        name = entry["item"].name
        if self.show_tree:
            name = name.rsplit("/", 1)[-1]

        yield name, "system"

    def format_node(self, entry):
        system = entry["item"].system
        if not self.show_tree and system.name:
            for output in self.format_system(dict(type="system", item=system)):
                yield output

            yield "/", None

        node_name = entry["item"].name.rsplit("/", 1)[-1]
        yield node_name, "node"

        parent_name = entry["item"].get("parent")
        if parent_name and self.show_inherits:
            yield "(", None
            yield parent_name, "nodeparent"
            yield ")", None

    def format_config(self, entry):
        if not self.show_tree:
            node = False
            for output in self.format_node(entry):
                node = True
                yield output

            if node:
                yield "/", None

        yield entry["config"].name, "config"

        parent_name = entry["config"].get("parent")
        if parent_name and self.show_inherits:
            yield "(", None
            yield parent_name, "configparent"
            yield ")", None

    def format_unknown(self, entry):
        yield "UNKNOWN: %r" % entry["type"], "red"

    def output(self):
        """Yields formatted strings ready for writing to the output file"""
        for text, color_code in self.output_pairs():
            yield self.color(text, color_code)

    def output_pairs(self):
        for entry in self.iter_tree():
            indent = (entry["item"]["depth"] - 1) * self.indent
            if entry["type"] not in ["system", "node", "config"]:
                indent += self.hindent

            if entry["type"] == "config":
                indent += self.indent


            type_code = "%stype" % entry["type"]
            if type_code not in colors.CODES:
                type_code = "reset"

            yield "%8s" % entry["type"], type_code
            yield "  ", None
            yield indent, None
            for output in self.formatters.get(entry["type"],
                                              self.format_unknown)(entry):
                yield output

            yield "\n", None


    def iter_tree(self):
        """
        Yields every system, node, config, etc. that needs to be produced to
        the output.
        """
        for item in self.confman.find(self.pattern, systems=self.show_systems,
                                      full_match=self.full_match):
            if isinstance(item, core.Node):
                if self.show_nodes:
                    yield dict(type="node", item=item)
            elif self.show_systems:
                yield dict(type="system", item=item)

            if self.show_node_prop:
                items = dict(item.showable())
                if self.list_props:
                    for key_path, value in util.path_iter_dict(items):
                        yield dict(type="prop", item=item,
                                   prop={key_path: value})
                else:
                    yield dict(type="prop", item=item, prop=items)

            if isinstance(item, core.Node):
                for conf in sorted(item.iter_configs(),
                                   key=lambda x: x.name):
                    if self.show_config:
                        yield dict(type="config", item=item, config=conf)

                    if self.show_config_prop:
                        yield dict(type="confprop", item=item, config=conf,
                                   prop=conf)

                    if self.show_settings:
                        for key, value in util.path_iter_dict(conf.settings):
                            yield dict(type="setting", item=item, config=conf,
                                       setting=key, value=value)

            cloud_prop = item.get("cloud", {})
            if self.show_cloud_prop and cloud_prop:
                if self.list_props:
                    for key_path, value in util.path_iter_dict(cloud_prop):
                        yield dict(type="cloud", item=item,
                                   prop={key_path: value})
                else:
                    yield dict(type="cloud", cloud=cloud_prop, item=item,
                               prop=cloud_prop)

            if self.query_status and cloud_prop.get("instance"):
                provider = self.tool.sky.get_provider(cloud_prop)
                status = provider.get_instance_status(cloud_prop)
                yield dict(type="status", item=item, status=status)