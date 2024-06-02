odoo.define('izi_dashboard.IZIViewDashboard', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var IZIViewDashboardBlock = require('izi_dashboard.IZIViewDashboardBlock');
    var IZIViewDashboard = Widget.extend({
        template: 'IZIViewDashboard',
        events: {
            'click input': '_onClickInput',
            'click button': '_onClickButton',
            'click .izi_update_script': '_onClickUpdateScript',
            'click .izi_view_dashboard_grid': '_onClickGrid',
        },

        /**
         * @override
         */
        init: function (parent) {
            this._super.apply(this, arguments);

            this.parent = parent;
            this.$grid;
            this.$editor;
            this.$editorContainer;
            this.selectedDashboard;
            this.$blocks = [];
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

        start: function () {
            var self = this;
            this._super.apply(this, arguments);
        },

        _getViewVisualByAnalysisId: function(analysis_id) {
            var self = this;
            var view_visual = false;
            self.$blocks.forEach(function (block) {
                if (block.analysis_id == analysis_id) {
                    view_visual = block.$visual;
                }
            });
            return view_visual;
        },

        _onClickUpdateScript: function (ev) {
            var self = this;
            var script = self.$editor.getValue();
            var analysis_id = parseInt($(ev.currentTarget).data('analysis-id'));
            var block_id = parseInt($(ev.currentTarget).data('block-id'));
            self._rpc({
                model: 'izi.analysis',
                method: 'write',
                args: [[analysis_id], {render_visual_script: script, use_render_visual_script: true}],
            }).then(function (res) {
                console.log('Update Script', res);
                self.$blocks.forEach(function (block) {
                    if (block.id == block_id) {
                        block.$visual._renderVisual();
                    }
                });
            });
        },
        
        _onClickGrid: function (ev) {
            var self = this;
            self.$editorContainer.hide();
        },
        _loadScriptEditor: function () {
            var self = this;
            // Query Editor
            ace.config.set('basePath', '/izi_dashboard/static/lib/ace-1.3.1/');
            ace.config.set('modePath', '/izi_dashboard/static/lib/ace-1.3.1/');
            ace.config.set('themePath', '/izi_dashboard/static/lib/ace-1.3.1/');
            ace.config.set('workerPath', '/izi_dashboard/static/lib/ace-1.3.1/');
            self.$editor = ace.edit('izi_script_editor');
            self.$editor.setTheme('ace/theme/chrome');
            self.$editor.setOption({ useWorker: false });
            self.$editor.session.setMode('ace/mode/javascript');
            self.$editorContainer = self.$('.izi_dashboard_script_editor');
            self.$editorContainer.draggable();
            self.$editorContainer.resizable();
        },

        /**
         * Private Method
         */
        _setDashboard: function(dashboard_id) {
            var self = this;
            self.selectedDashboard = dashboard_id;
        },
        _loadDashboard: function (filters, mode=false) {
            var self = this;
            self._clear();
            if (self.selectedDashboard) {
                self._rpc({
                    model: 'izi.dashboard.block',
                    method: 'search_read',
                    args: [[['dashboard_id', '=', self.selectedDashboard]], ['id', 'gs_x', 'gs_y', 'gs_w', 'gs_h', 'min_gs_w', 'min_gs_h', 'analysis_id', 'animation', 'refresh_interval', 'visual_type_name', 'rtl']],
                }).then(function (res) {
                    // console.log('Load Dashboard', res);
                    self.dashboardBlocks = res;
                    // Init Grid
                    if (!self.$grid) {
                        self.$grid = GridStack.init();
                        self.$grid.margin(7);
                        self.$grid.float('true');
                        self.$grid.cellHeight(125);
                    }
                    self.$grid.enableMove(false);
                    self.$grid.enableResize(false);
                    self.$grid.removeAll();
                    // For Each Dashboard Block
                    var nextY = 0;
                    var index = 0;
                    self.dashboardBlocks.forEach(block => {
                        var isScoreCard = false;
                        if (block.visual_type_name && block.visual_type_name.toLowerCase().indexOf("scrcard") >= 0)
                            isScoreCard = true;
                        if (mode == 'ai_analysis') {
                            if (isScoreCard) {
                                block.gs_x = 0;
                                block.gs_h = 2;
                                block.gs_w = 12;
                            } else {
                                block.gs_x = 0;
                                block.gs_h = 4;
                                block.gs_w = 12;
                            }
                        }
                        var widgetValues = {
                            'id': block.id,
                            'w': block.gs_w,
                            'h': block.gs_h,
                            'x': block.gs_x,
                            'y': block.gs_y,
                            'minW': block.min_gs_w,
                            'minH': block.min_gs_h,
                            // 'autoPosition': 'true',
                        }
                        if (window.innerWidth <= 792 || mode == 'ai_analysis') {
                            widgetValues.y = nextY;
                            nextY += widgetValues.h;
                        }
                        self.$grid.addWidget(widgetValues);
                        // Init IZIViewDashboardBlock
                        if (block.analysis_id) {
                            var args = {
                                'id': block.id,
                                'analysis_id': block.analysis_id[0],
                                'analysis_name': block.analysis_id[1],
                                'animation': block.animation,
                                'filters': filters,
                                'refresh_interval': block.refresh_interval,
                                'index': index,
                                'mode': mode,
                                'visual_type_name': block.visual_type_name,
                                'rtl': block.rtl,
                            }
                            index += 1;
                            var $block = new IZIViewDashboardBlock(self, args);
                            $block.appendTo($(`.grid-stack-item[gs-id="${block.id}"] .grid-stack-item-content`));
                            self.$blocks.push($block);
                        }
                    });
                });
            }
        },

        _clear() {
            var self = this;
            self.$blocks.forEach($block => {
                $block.clearInterval();
                $block.destroy();
            })
            self.$blocks = [];
        },

        _removeItem(id) {
            this.$grid.engine.nodes = (this.$grid.engine.nodes).filter(object => {
                return object.id !== id;
              });
            $(`.grid-stack-item[gs-id="${id}"]`).remove();
        },

        _onClickInput: function(ev) {
            var self = this;
        },

        _onClickButton: function (ev) {
            var self = this;
        }
    });

    return IZIViewDashboard;
});