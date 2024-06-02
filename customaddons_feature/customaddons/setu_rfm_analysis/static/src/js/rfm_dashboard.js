odoo.define("setu_rfm_analysis.rfm_dashboard", function (require) {
"use strict";

var core = require('web.core');
var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var time = require('web.time');
var web_client = require('web.web_client');
var _t = core._t;
var QWeb = core.qweb;
var COLORS = ["#1f77b4", "#aec7e8"];
var field_utils = require('web.field_utils');
var FORMAT_OPTIONS = {
    // allow to decide if utils.human_number should be used
    humanReadable: function (value) {
        return Math.abs(value) >= 1000;
    },
    // with the choices below, 1236 is represented by 1.24k
    minDigits: 1,
    decimals: 2,
    // avoid comma separators for thousands in numbers when human_number is used
    formatterCallback: function (str) {
        return str;
    },
};
var RfmDashboardAction = AbstractAction.extend({
    hasControlPanel: true,
    contentTemplate: 'setu_rfm_analysis.RfmDashboardMain',
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    events: {
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.DATE_FORMAT = time.getLangDateFormat();
        this.date_range = 'week';  // possible values : 'week', 'month', year'
        this.date_from = moment.utc();//.subtract(1, 'week')
        this.date_to = moment.utc();

        this.graphs = [];
        this.chartIds = {};
    },
    willStart: function() {
        var self = this;
        return Promise.all([ajax.loadLibs(this), this._super()]).then(function() {
            return self.fetch_data();
        })
    },

    start: function() {
        var self = this;
//        this._computeControlPanelProps();
        return self._super.apply(this, arguments)
    },
    on_attach_callback: function () {
        this.render_graphs(this.chart_values);
        this._super.apply(this, arguments);
    },
    on_detach_callback: function () {
        this._isInDom = false;
        this._super.apply(this, arguments);
    },
    fetch_data: function() {
        var self = this;
        var prom = this._rpc({
            route: '/setu_rfm_analysis/fetch_dashboard_data',
            params: {
                date_from: this.date_from.year()+'-'+(this.date_from.month()+1)+'-'+this.date_from.date(),
                date_to: this.date_to.year()+'-'+(this.date_to.month()+1)+'-'+this.date_to.date(),
                company_id: self.controlPanelProps.action.context.allowed_company_ids
            },
        });
        prom.then(function (result) {
                self.chart_values = result
        });
        return prom;
    },
    formatValue: function (value) {
        var formatter = field_utils.format.float;
        var formatedValue = formatter(value, undefined, FORMAT_OPTIONS);
        return formatedValue;
    },
    getRandomRgb: function() {
      var num = Math.round(0xffffff * Math.random());
      var r = num >> 16;
      var g = num >> 8 & 255;
      var b = num & 255;
      return 'rgb(' + r + ', ' + g + ', ' + b + ', 0.7)';
    },
    render_dashboards: function() {
        var self = this;
        self.$('.o_rfm_dashboard').append(QWeb.render('setu_rfm_analysis.dashboard_content', {widget: self}));
    },
    render_graphs: function(chart_values) {
        var self = this;
        $.each(self.chart_values, function(index, chartvalue){
            var $canvasContainer = $('<div/>', {class: 'o_graph_canvas_container'});
            self.$canvas = $('<canvas/>');
            $canvasContainer.append(self.$canvas);
            self.$('#'+chartvalue.chart_name).append($canvasContainer);
            var ctx = self.$canvas[0];
            ctx.height = 106

            if (chartvalue.chart_name == 'customer_rating'){
                var labels = chartvalue.integration_labels
            }
            else{
                var labels = chartvalue.chart_values[0].values.map(function (value) {
                return value.name
            });
            }
            /*if(chartvalue.chart_name == 'customer_rating'){
            	var labels_1 = chartvalue.chart_values.map(function (group, index) {
            	return group.values.map(function (value) {
                        return value.name;
                    })
            	});
                var labels_1 = [].concat.apply([], labels_1); 
                var labels = _.union(labels,labels_1);
		}*/

            if (chartvalue.chart_name == 'customer_rating'){
                 var datasets = chartvalue.chart_values
            }
            else {
                var datasets = chartvalue.chart_values.map(function (group, index) {
                    return {
                        label: group.key,
                        data: group.values.map(function (value) {
                            return value.count;
                        }),
                        labels: group.values.map(function (value) {
                            return value.name;
                        }),
                        backgroundColor: chartvalue.chart_type == 'bar'? self.getRandomRgb() : group.values.map(function (value) {
                            return self.getRandomRgb()
                        }),
                        borderWidth: 1
                    };
                });
            }

            const data = {
              labels: labels,
              datasets: datasets
            };
            const options = {
                    title: {
                        display: true,
                        text: chartvalue.chart_title,
                        position: 'bottom',
                    }
                }
            if(chartvalue.chart_type == 'bar'){
                options.scales = {
                            yAxes: [{
                                ticks: {
                                    beginAtZero: true
                                }
                            }]
                        }
            }
            self.chart = new Chart(ctx, {
                type: chartvalue.chart_type,
                data: data,
                 options: options
            });
        });


    },
    _computeControlPanelProps() {
        const $searchview = $(QWeb.render("setu_rfm_analysis.DateRangeButtons", {
            widget: this,
        }));
        $searchview.find('button.js_date_range').click((ev) => {
            $searchview.find('button.js_date_range.active').removeClass('active');
            $(ev.target).addClass('active');
            this.on_date_range_button($(ev.target).data('date'));
        });
        this.controlPanelProps.cp_content = { $searchview };
    },

    on_date_range_button: function(date_range) {
        if (date_range === 'week') {
            this.date_range = 'week';
            this.date_from = moment.utc().subtract(1, 'weeks');
        } else if (date_range === 'month') {
            this.date_range = 'month';
            this.date_from = moment.utc().subtract(1, 'months');
        } else if (date_range === 'year') {
            this.date_range = 'year';
            this.date_from = moment.utc().subtract(1, 'years');
        } else {
            console.log('Unknown date range. Choose between [week, month, year]');
            return;
        }

        var self = this;
        Promise.resolve(this.fetch_data()).then(function () {
            self.$('.o_rfm_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });

    },
})
core.action_registry.add('rfm_dashboard_client_action', RfmDashboardAction);

return RfmDashboardAction;

});
