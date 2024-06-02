/** @odoo-module **/
import {attr, many2many, many2one, one2many, one2one} from '@mail/model/model_field';
import {
    registerFieldPatchModel,
    registerIdentifyingFieldsPatch,
    registerInstancePatchModel,
    registerClassPatchModel
} from '@mail/model/model_core';
// registerFieldPatchModel('mail.discuss', 'advanced_helpdesk/static/src/components/discuss/s_discuss.js', {
//     s_is_fold_filter: attr(),
// });
registerInstancePatchModel('mail.discuss', 'advanced_helpdesk/static/src/components/discuss/s_discuss.js', {
    _created() {
        const res = this._super(...arguments);
        const s_is_fold_filter = false;
        this.onClickFoldFilter = this.onClickFoldFilter.bind(this);
        this.booOnClickUnread = this.booOnClickUnread.bind(this);
        this.booOnClickAll = this.booOnClickAll.bind(this);
        this.booOnClickRead = this.booOnClickRead.bind(this);
        return res;
    },
    setPointerEvents () {
        var channel_arr = $('.o_DiscussSidebarCategory_header > .o_DiscussSidebarCategory_title')
        if (!channel_arr.length > 0) {
            return -1;
        } else {
            var icon_filter = $('.o_DiscussSidebarCategory_header > .o_DiscussSidebarCategory_title > .o_DiscussSidebarCategory_titleIcon.fa-chevron-right');
            if (icon_filter.length > 0) {
                icon_filter.trigger("click");
            }
            channel_arr.css({"pointer-events": "none"});
            return channel_arr;
        }
    },
    async booOnClickUnread(ev) {
        this.booSelectedFilter(ev)
        this.setPointerEvents()
        var channel = $('.o_DiscussSidebarCategory_content .o_DiscussSidebarCategoryItem');
        if (channel.length > 0) {
            channel.each(function (index) {
                if (!channel[index].classList.contains('o-unread')) {
                    channel[index].style.display = 'none'
                } else {
                    channel[index].style.display = 'flex'
                }
            });
        }
    },
    async booOnClickRead(ev) {
        this.booSelectedFilter(ev)
        this.setPointerEvents()
        var channel = $('.o_DiscussSidebarCategory_content .o_DiscussSidebarCategoryItem');
        if (channel.length > 0) {
            channel.each(function (index) {
                if (channel[index].classList.contains('o-unread')) {
                    channel[index].style.display = 'none'
                } else {
                    channel[index].style.display = 'flex'
                }
            });
        }
    },
    async booOnClickAll(ev) {
        this.booSelectedFilter(ev)
        var channel_arr = this.setPointerEvents()
        channel_arr.css({"pointer-events": "auto"})
        var channel = $('.o_DiscussSidebarCategory_content .o_DiscussSidebarCategoryItem');
        if (channel.length > 0) {
            channel.each(function (index) {
                channel[index].style.display = 'flex'
            });
        }
    },
    booSelectedFilter(ev) {
        var selected_filter = $('.o_DiscussSidebarMailbox.s_filter_channel.o-active');
        if (selected_filter.length > 0) {
            selected_filter.each(function (index) {
                selected_filter[index].classList.remove('o-active');
            });
        }
        if (typeof ev !== 'undefined') {
            ev.target.classList.add('o-active')
        }
    },
    onClickFoldFilter(ev) {
        var is_fold_filter = $('.o_DiscussSidebarCategory_titleIcon.is_fold_filter');
        var selected_filter = $('.o_DiscussSidebarMailbox.s_filter_channel');
        if (is_fold_filter.length > 0) {
            if (is_fold_filter[0].classList.contains('fa-chevron-right')) {
                is_fold_filter[0].classList.remove('fa-chevron-right');
                is_fold_filter[0].classList.add('fa-chevron-down');
                if (selected_filter.length > 0) {
                    selected_filter.each(function (index) {
                        selected_filter[index].style.display = 'flex'
                    });
                }
            } else if (is_fold_filter[0].classList.contains('fa-chevron-down')) {
                is_fold_filter[0].classList.add('fa-chevron-right');
                is_fold_filter[0].classList.remove('fa-chevron-down');
                if (selected_filter.length > 0) {
                    selected_filter.each(function (index) {
                        selected_filter[index].style.display = 'none'
                    });
                }
            }
        }
    }
});

