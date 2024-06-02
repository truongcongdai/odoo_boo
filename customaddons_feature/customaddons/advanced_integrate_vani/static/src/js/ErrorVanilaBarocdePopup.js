odoo.define('advanced_integrate_vani.ErrorBarcodePopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    class ErrorVanilaBarcodePopup extends ErrorPopup {
        get translatedMessage() {
            return this.env._t(this.props.message);
        }
    }
    ErrorVanilaBarcodePopup.template = 'ErrorVanilaBarcodePopup';
    ErrorVanilaBarcodePopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: _lt('Error'),
        body: '',
        message:
            _lt('Chưa có Vanila Barcode trên hệ thống, vui lòng kết nối BOO trên Vani'),
    };

    Registries.Component.add(ErrorVanilaBarcodePopup);

    return ErrorVanilaBarcodePopup;
});
