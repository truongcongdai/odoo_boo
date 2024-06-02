$(document).ready(function () {
    $('#city_id').change(function () {
        var selectedCityId = $(this).val();

        // Make an AJAX request to get the districts for the selected city
        $.ajax({
            url: '/get_districts',
            data: {
                city_id: selectedCityId
            },
            success: function (response) {
                // Clear the district dropdown
                $('#country_district_id').empty();

                // Populate the district dropdown with the new options
                response.districts.forEach(function (district) {
                    $('#country_district_id').append($('<option>', {
                        value: district.code,
                        text: district.name
                    }));
                });
            }
        });
    });

    // Disable the submit button on page load
    $('input[type="submit"]').prop('disabled', true);

    $('#confirm_info').change(function () {
        if ($(this).is(":checked")) {
            $('input[type="submit"]').prop('disabled', false);
        } else {
            $('input[type="submit"]').prop('disabled', true);
        }
    });
});