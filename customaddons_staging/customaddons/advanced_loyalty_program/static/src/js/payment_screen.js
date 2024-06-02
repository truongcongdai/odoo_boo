function send_otp_zns(phone_number, zalo_zns_template_id, cid_order, type_otp) {
    return rpc.query({
        model: 'sms.sms',
        method: 'send_otp_zns',
        args: [0, phone_number, zalo_zns_template_id, cid_order, type_otp],
    }).then(function (otp) {
        return otp;
    });
}

function countdown(customer_phone) {
    var check_customer_phone = document.getElementsByClassName('phone-number');
    var timeleft = 300;
    var downloadTimer = setInterval(function(){
        timeleft--;
        const count_down_timer = document.getElementById("countdowntimer");
        if (count_down_timer) {
            if (customer_phone === check_customer_phone) {
                count_down_timer.textContent = timeleft + ' giây';
            }
        }
        if(timeleft <= 0)
            clearInterval(downloadTimer);
    }, 1000);
}

function send_back_otp() {
    var customer_phone = document.getElementsByClassName('phone-number');
    var zalo_template = document.getElementsByClassName('zalo-zns-template-id');
    countdown(customer_phone);
    if (phone_number && zalo_zns_template_id) {
        var phone_number = customer_phone[0].textContent;
        var zalo_zns_template_id = zalo_template[0].textContent;
        send_otp_zns(phone_number, zalo_zns_template_id,null ,'pos');
    }
}