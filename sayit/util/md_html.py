from misaka import Markdown, HtmlRenderer


render = HtmlRenderer(flags=('hard-wrap', 'escape'))
to_html = Markdown(render, extensions=('fenced-code',
                                       'tables',
                                       'no-intra-emphasis'))
