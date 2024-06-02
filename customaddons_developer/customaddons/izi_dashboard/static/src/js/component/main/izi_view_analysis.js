odoo.define('izi_dashboard.IZIViewAnalysis', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    
    var IZIViewVisual = require('izi_dashboard.IZIViewVisual');
    var IZISelectFilterTemp = require('izi_dashboard.IZISelectFilterTemp');
    var IZIViewAnalysis = Widget.extend({
        template: 'IZIViewAnalysis',
        events: {
            'click .izi_view_analysis_explore_container': '_onClickAnalysisExpore',
            'click .izi_submit_analysis_explore': '_onClickSubmitAnalysisExpore',
            'click .izi_view_analysis_explore_bg': '_onClickBgAnalysisExpore',
        },

        /**
         * @override
         */
        init: function (parent) {
            var self = this;
            this._super.apply(this, arguments);
            
            self.parent = parent;
            self.$visual;
            self.$title;
            self.$filter;
            self.analysis_id;
            self.selectedAnalysisExplores = [];
            self.selectedDashboardExplore;
        },

        willStart: function () {
            var self = this;

            return this._super.apply(this, arguments).then(function () {
                return self.load();
            });
        },

        load: function () {
            var self = this;
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);

            am4core.useTheme(am4themes_animated);

            self.$title = self.$el.find('.izi_dashboard_block_header .izi_dashboard_block_title');
            
            // Add Component Visual View
            self.$visual = new IZIViewVisual(self);
            self.$visual.appendTo(self.$el.find('.izi_dashboard_block_content'));

            // Add Component Filters
            self.$filter = new IZISelectFilterTemp(self, self.$visual);
            self.$filter.appendTo(self.$el.find('.izi_dashboard_block_header'));

            // Analysis Explore
            self.$viewAnalysisExplore = self.$('.izi_view_analysis_explore');
        },

        _getViewVisualByAnalysisId: function (analysis_id) {
            var self = this;
            if (self.$visual.analysis_id == analysis_id)
                return self.$visual;
            return false;
        },

        _setAnalysisId: function (analysis_id) {
            var self = this;
            self.analysis_id = analysis_id;
            if (self.$filter) {
                self.$filter.analysis_id = analysis_id;
                self.$filter._loadFilters();
            }
        },

        _onClickBgAnalysisExpore: function (ev) {
            var self = this;
            self.$viewAnalysisExplore.closest('.izi_dialog').hide();
        },

        _onClickAnalysisExpore: function (ev) {
            var self = this;
            var analysis_id = $(ev.currentTarget).data('analysis-id');
            if ($(ev.currentTarget).hasClass('active')) {
                $(ev.currentTarget).removeClass('active');
                // Check if analysis_id is in selectedAnalysisExplores
                var index = self.selectedAnalysisExplores.indexOf(analysis_id);
                if (index > -1) {
                    self.selectedAnalysisExplores.splice(index, 1);
                }
            } else {
                $(ev.currentTarget).addClass('active');
                // Check if analysis_id is not in selectedAnalysisExplores
                var index = self.selectedAnalysisExplores.indexOf(analysis_id);
                if (index == -1) {
                    self.selectedAnalysisExplores.push(analysis_id);
                }
                
            }
        },

        _onClickSubmitAnalysisExpore: function (ev) {
            var self = this;
            new swal({
                title: "Confirmation",
                text: `
                    Do you confirm to save the selected analysis (${self.selectedAnalysisExplores.length})?
                `,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: 'Yes',
                heightAuto : false,
            }).then((result) => {
                if (result.isConfirmed) {
                    console.log(self.selectedAnalysisExplores);
                    self._rpc({
                        model: 'izi.analysis',
                        method: 'save_lab_analysis_explore',
                        args: [self.selectedAnalysisExplores, self.selectedDashboardExplore],
                    }).then(function (result) {
                        new swal('Success', `Analysis has been successfully saved`, 'success');
                        self.$viewAnalysisExplore.closest('.izi_dialog').hide();
                    });
                }
            });
        },
    });

    return IZIViewAnalysis;
});