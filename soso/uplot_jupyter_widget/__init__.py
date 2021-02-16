import asyncio
import typing

import jp_proxy_widget
from traitlets import Bool, Dict, Int, List, Unicode

__all__ = ['uPlotWidget']

class uPlotWidget(jp_proxy_widget.JSProxyWidget):  # type: ignore

    css = Unicode(
        'https://raw.githubusercontent.com/leeoniya/uPlot/master/dist/uPlot.min.css',  # noqa: E501
        allow_none=False)
    js = Unicode(
        'https://raw.githubusercontent.com/leeoniya/uPlot/master/dist/uPlot.iife.min.js',  # noqa: E501
        allow_none=False)

    data = List([])
    # For options that expect a function, for example, DateFormatterFactory,
    # include the javascript as a string but prefix it with __js_eval. For
    # example: 'opt': '__js_eval:() => console.log("HELLO")'
    opts = Dict({})

    max_datapoints = Int(None, allow_none=True)
    auto_resize = Bool(False, allow_none=False).tag(sync=True)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super(uPlotWidget, self).__init__(*args, **kwargs)
        self.load_css(self.css)
        self.load_js_files([self.js])

        self.__make_plot()

    def __make_plot(self) -> None:
        self.js_init("""
        function __replace_recursive(obj) {
          for(var key in obj) {
            let value = obj[key];
            if((typeof value == "string") && value.startsWith("__js_eval:")) {
              obj[key] = eval(value.replace("__js_eval:",""));
            } else if (value.constructor == Object){
              __replace_recursive(value);
            } else if (Array.isArray(value)) {
              for(var elem of value) {
                __replace_recursive(elem);
              }
            }
          }
        }

        this.el.innerHTML = '';
        __replace_recursive(opts);
        let plot = new uPlot(opts,data,this.el);
        element.__plot = plot;

        element.replace_data = (rows) => {
          plot.setData(rows,true);
        }

        element.push_data = (row,max_data) => {
          let data = plot.data.slice(0);
          // uPlot requires null, not NaN
          for(let ii = 0; ii < row.length; ++ii) {
            if(isNaN(row[ii])) row[ii] = null;
          }
          let ii;
          // if the time point is the same
          if(row[0] == data[0][data[0].length-1]) {
            // just update the last row
            for(ii = 0; ii < row.length; ++ii) {
              data[ii][data[ii].length-1] = row[ii];
            }
          } else { // new timepoint
            for(ii = 0; ii < row.length; ++ii) {
              data[ii].push(row[ii]);
            }
          }
          if (typeof(max_data) == 'number') {
            for(ii =0; ii < row.length; ++ii) {
              if(data[ii].length < max_data) continue;
              data[ii] = data[ii].slice(-max_data);
            }
          }
          plot.setData(data,true);
        };

        __update_size = () => {
            const auto_resize = this.model.get('auto_resize');
            if(!auto_resize) return;

            const element = this.el;
            const title = this.el.querySelector(".u-title");
            const legend = this.el.querySelector(".u-legend");

            const height = element.clientHeight - title.clientHeight - legend.clientHeight;
            const width = element.clientWidth;

            if (isNaN(height) || isNaN(width)) return;
            console.log("Resizing uPlot widget",{height:height,width:width});
            plot.setSize({
                height: height,
                width: width
            });
        }

        // Initial resize
        setTimeout(__update_size,1000);

        // https://davidwalsh.name/javascript-debounce-function
        function __debounce(func, wait, immediate) {
            var timeout;
            return function() {
                var context = this, args = arguments;
                var later = function() {
                    timeout = null;
                    if (!immediate) func.apply(context, args);
                };
                var callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func.apply(context, args);
            };
        };


        this.el.addEventListener("resize",__debounce(__update_size,250));
        window.addEventListener("resize",__debounce(__update_size,250));

        """,
                     data=self.data,
                     opts=self.opts)

    def push_data(self, row: typing.List[float]) -> None:
        self.element.push_data(row, self.max_datapoints)

    def replace_data(self, data: typing.List[typing.List[float]]) -> None:
        if self.max_datapoints is not None:
            data = data[-self.max_datapoints:]
        self.element.replace_data(data)

    async def get_data_async(self) -> typing.List[typing.List[float]]:
        def cb(value: typing.List[typing.List[float]]) -> None:
            assert not fut.done()
            fut.set_result(value)

        fut: asyncio.Future[typing.List[typing.List[float]]] = asyncio.Future()
        self.get_value_async(cb, 'element.__plot.data')
        await fut
        return fut.result()
