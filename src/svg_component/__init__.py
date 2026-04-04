import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "interactive_svg",
    path=os.path.dirname(os.path.abspath(__file__))
)

def interactive_svg(svg_code, height=270, key=None):
    return _component_func(svg_code=svg_code, height=height, key=key)
