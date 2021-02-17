// Note: this code expects to be executed in js_init
function __jseval_recursive(obj) {
    __eval_recursive = (obj,key) => {
        const value = obj[key];
        if((typeof value == "string") && value.startsWith("__js_eval:")) {
            obj[key] = eval(value.replace("__js_eval:",""));
        } else if (value.constructor == Object){
            __jseval_recursive(value);
        } else if (Array.isArray(value)) {
            for(let key in value) {
                __eval_recursive(value,key);
            }
        }
    };
    for(let key in obj) {
        __eval_recursive(obj,key);
    }
}

this.el.innerHTML = '';
__jseval_recursive(opts);
let plot = new uPlot(opts,data,this.el);
element.__plot = plot;

element.replace_data = (rows) => {
    plot.setData(rows,true);
    __update_size();
};

var __push_data = (row,max_data) => {
    let data = plot.data.slice(0);
    let forceRecalcAxes = false;
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
        forceRecalcAxes = true;
    }
    if (typeof(max_data) == 'number') {
        for(ii =0; ii < row.length; ++ii) {
            if(data[ii].length < max_data) continue;
            data[ii] = data[ii].slice(-max_data);
        }
    }
    // In case we are zoomed into a selection when data is pushed, we only want
    // to recalculate axes if we get a new timepoint.
    plot.setData(data,forceRecalcAxes);
    if(!forceRecalcAxes) {
        plot.redraw(false,false);
    }
};

const self = this;
// overwrite jp_proxy_widget message handling
// because protocol is too chatty otherwise for quick updates.
const old_handle_custom_message = self.handle_custom_message.bind(self);
self['handle_custom_message'] = function(content,buffers,widget) {
    if(content['command'] == '__uplot_push_data') {
        const row = content['payload'][0];
        const max_data = content['payload'][1];
        __push_data(row,max_data);
    } else {
        old_handle_custom_message(content,buffers,widget);
    }
};

__update_size = () => {
    const auto_resize = this.model.get('auto_resize');
    if(!auto_resize) return;

    const element = this.el;
    const title = this.el.querySelector(".u-title");
    const legend = this.el.querySelector(".u-legend");

    const titleHeight = !!title ? title.clientHeight : 0;
    const legendHeight = !!legend ? legend.clientHeight : 0;

    const height = element.clientHeight - titleHeight - legendHeight; // # noqa
    const width = element.clientWidth;

    if (isNaN(height) || isNaN(width)) return;
    plot.setSize({
        height: height,
        width: width
    });
};

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

console.log("uplot_jupyter_widget:js_init done",element);
