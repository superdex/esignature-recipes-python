// Javascript for API logging

;(function ($) {
  
	// Private global variabls for the functions
	var toc_items = [], // array of the notification items that are being displayed
		ace_editor = false,
        ace_cdn = "https://cdnjs.cloudflare.com/ajax/libs/ace/1.2.3/"; // Where ACE loads optional JS from
    
    // FORMAT OF THE TOC ENTRIES
    // toc_entries is an array. The element [0] is the oldest, shown at the bottom of the page.
    // Each entry is {
    //    success: boolean -- was the call successful?
    //    url: the url for retrieving the call
    //    file_name: the raw file_name. Can be used for sorting the entries
    //    x_ray: false if no x_ray header. Otherwise the contents of the header
    //    method: GET, POST, etc
    //    request_url: the complete request url
    //    method_name: the method name used in the log file name
    //    body: the NOT uuencoded first 1500 bytes of the log entry
    //    date_time: the call was made before this time
    // }
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////

    // Page-specific JS: API Logging page
    function add_API_Logs_page_listeners() {
        // Add listener for the logging-status-refresh
        //     ... logging status: <span id="logging-status">tbd</span><span></span><a href="#" id="logging-status-refresh">Refesh<
        $('#logging-status-refresh').click(logging_status);
        logging_status(); // Run it once pro-actively on page load

        // Add listener for download
        // <button type="button" class="btn btn-primary marginleft" id="logging-download" data-feedback="feedback-download">Download Logs</button>
        var feedback = $('#logging-download').attr("data-feedback");
        $('#logging-download').click(feedback, logs_download);
        logs_download({data: feedback}); // Run it once pro-actively on page load
    }
    
    var logging_status = function _logging_status(e) {
        var logging_status = $("#logging-status"),
            counter_el = $(logging_status).next()[0],
            countdown_i,
            countdown = function () {
                countdown_i -= 1;
                $(counter_el).text(countdown_i)
            },
            countdown_id;

        $(logging_status).text("Working... ");
        countdown_i = 100;
        countdown_id = setInterval(countdown, 300);
        $.ajax({
            url: "logging_status?" + Date.now(), type: "GET",
            contentType: "application/json; charset=utf-8", dataType: "json"
        })
            .done(function (data, textStatus, jqXHR) {
                if (data.err) {
                    $(loging_status).html("<b>Problem:</b> " + data.err);
                } else {
                    $(logging_status).html(data.status);
                }
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                $(logging_status).html("<b>Problem:</b> " + textStatus);
            })
            .always(function () {
                clearInterval(countdown_id);
                $(counter_el).text("")
            });
    }
    
    var logs_download = function _logs_download(e){
        var feedback = e.data,
            feedback_el = $("#" + feedback),
            counter_el = $(feedback_el).next()[0],
            countdown_i,
            countdown = function(){countdown_i -= 1; $(counter_el).text(countdown_i)},
            countdown_id;
        $(feedback_el).text("Working... ");
        countdown_i = 100; countdown_id = setInterval(countdown, 300);
        $.ajax({
            url: "logs_download", type: "POST",
            contentType: "application/json; charset=utf-8", dataType: "json"})
            .done(function(data, textStatus, jqXHR) {
                if (data.err) {
                    $(feedback_el).html("<b>Problem:</b> " + data.err);
                } else {
                    $(feedback_el).html("");
                    process_new_items(data);
                }
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                $(feedback_el).html("<b>Problem:</b> " + textStatus);
            })
            .always(function(){clearInterval(countdown_id); $(counter_el).text("")});
    }


	function process_new_items(data){
		// Process the list of items
		// The data is an array of raw log entries format:
		// { file_name: "T2016-07-17T13_51_07__00_OK_GetAccountSharedAccess.txt"
        //   head: base64 version of first 1500 char of the log file
        //   url: url for retrieving the complete file
		// }
        //
        // 
        data = data.new_entries;
		if (data.length == 0) {return;} // nothing to do...

		// Sort the incoming events so the newest (_00) is first.
		data.sort(function (a, b) {
			return (a.file_name > b.file_name) ? -1 : 1; // compare the file names
        });

        // process each new entry
		data.forEach (function(val, index, arr){add_to_toc(examine(val))});
    }
	
    function examine(item){
        // Compute the item's information
        //    success: boolean -- was the call successful?
        //    url: the url for retrieving the call
        //    file_name: the raw file_name. Can be used for sorting the entries
        //    x_ray: false if no x_ray header. Otherwise the contents of the header
        //    method: GET, POST, etc
        //    request_url: the complete request url
        //    method_name: the method name used in the log file name
        //    head: the NOT uuencoded first 1500 bytes of the log entry
        //    date_time: the call was made before this time

        item.head = window.atob(item.head);
   		//  file_name: "T2016-07-17T13_51_07__00_OK_GetAccountSharedAccess.txt"

        var // See https://regex101.com/#javascript for testing
            re_success = /(_OK_)|(_Created_)/,
            success = re_success.test(item.file_name),
            re_x_ray = /\nX\-ray: (.*)\n/m,
            re_x_ray_r = re_x_ray.exec(item.head),
            x_ray = re_x_ray_r ? re_x_ray_r[1] : false,
            re_method_url = /^([A-Z]*) (.*)/,
            re_method_url_r = re_method_url.exec(item.head),
            method = re_method_url_r ? re_method_url_r[1] : false,
            request_url = re_method_url_r ? re_method_url_r[2] : false,
            re_time_method = /T(\w*-\w*-\w*_\w*_\w*)__\w*_(\w*)/,
            re_time_method_r = re_time_method.exec(item.file_name),
            method_name = re_time_method_r ? re_time_method_r[2] : false,
            date_time = re_time_method_r ? re_time_method_r[2].replace("_", ":").replace("T", " ") : false;
        
        item.success = success;
        item.x_ray = x_ray;
        item.method = method;
        item.request_url = request_url;
        item.method_name = method_name;
        item.date_time = date_time;
        return item;
    }

	function add_to_toc(item){
        
        // Set css class depending on success field
        item.css_class = item.success ? "success-circle" : "failure-circle";
        
		toc_items.push(item); // We're assuming that we won't receive an item out of order.
		// Create the new li by using mustache with the template
	    var rendered = Mustache.render($('#toc_item_template').html(), item);
		prependListItem("toc", rendered);
		// The new item is now the first item in the toc ul.
		$("#toc").children().first().click(item, show_item).tooltip(); // See http://getbootstrap.com/javascript/#tooltips
	}
	
	function prependListItem(listName, listItemHTML){
		// See http://stackoverflow.com/a/1851486/64904
	    $(listItemHTML)
	        .hide()
	        .css('opacity',0.0)
	        .prependTo('#' + listName)
	        .slideDown('slow')
			.animate({opacity: 1.0});
		window_resized();
	}

	var show_item = function(event) {
		// This is a jQuery event handler. See http://api.jquery.com/Types/#Event
		// It fills in the main column
		var item = event.data, // our object about the xml notification
			item_info_el = $("#xml_info");
	
		$(item_info_el).html("<h2>Working...</h2>");
		$.ajax({
			url: item.xml_url,
       		type: 'get',
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
		    $(item_info_el).html("<h3>Problem: Couldn’t fetch the xml file</h3><p>" + textStatus + "</p>");
		})
		.done(function(data, textStatus, jqXHR) {	
			var xml_pretty = xml_make_pretty(jqXHR.responseText),
				rendered = Mustache.render($('#xml_file_template').html(), item);
			$(item_info_el).html(rendered);
			if (! ace_editor) {
                ace.config.set("workerPath", ace_cdn);
				ace_editor = ace.edit("editor");
				ace_editor.setReadOnly(true);
    			ace_editor.setTheme("ace/theme/chrome");
			    ace_editor.setOption("wrap", "free");
				ace_editor.$blockScrolling = Infinity;
				window_resized();
			    var XMLMode = ace.require("ace/mode/xml").Mode,
				    ace_session = ace_editor.getSession();
				ace_session.setMode(new XMLMode());
				ace_session.setUseWrapMode(true);
				ace_session.setFoldStyle("markbeginend");
			}
			ace_editor.setValue(xml_pretty);
			ace_editor.getSelection().clearSelection();
			ace_editor.getSelection().moveCursorToScreen(0,0,true);
		})
	}

	var window_resized = function(){
		// resize left column
		var available = window.scrollHeight ? window.scrollHeight : $(window).height(),
			h = available -  $("#status_left").position().top; 
			// At least for Chrome, scrollHeight is only defined if there is a scrollbar
		
		if ($(window).width() > 991) { $("#status_left").height(h); }
		
		// resize editor div, 300 min
		var min = 300;
		if (ace_editor) {			
			h = $(window).height() - $("#editor").offset().top - $(".navbar").height() - 5;
			// The navbar is fixed so offset doesn't include it. (?)

			$("#editor").height((h < min) ? min : h);
			ace_editor.resize();
		}
	}

	var countdown = function(){
		// Update the countdown value
		countdown_i -= 1;
		$("#counter").text(countdown_i);
	}
	
	function stop_countdown(){
		if (! countdown_interval_id) {return;}
		clearInterval(countdown_interval_id);
		countdown_interval_id = false;
		$("#countdown").hide();
		$("#xml_info").html("<h1 class='toc-instructions'>← Click an item to see the XML file</h1>");
	}
	
	function working_show(){
		$("#working").removeClass("workinghide").addClass("workingshow");
	}
	
	function working_hide(){
		$("#working").removeClass("workingshow").addClass("workinghide");
	}
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	
	function xml_make_pretty (xml) {
		// From https://gist.github.com/sente/1083506
		var formatted = '',
		    reg = /(>)(<)(\/*)/g,
			pad = 0,
			pad_content = "    ";
			
		xml = xml.replace(reg, '$1\r\n$2$3');

		jQuery.each(xml.split('\r\n'), function(index, node) {
		    var indent = 0;
		    if (node.match( /.+<\/\w[^>]*>$/ )) {
		        indent = 0;
		    } else if (node.match( /^<\/\w/ )) {
		        if (pad != 0) {
		            pad -= 1;
		        }
		    } else if (node.match( /^<\w[^>]*[^\/]>.*$/ )) {
		        indent = 1;
		    } else {
		        indent = 0;
		    }

		    var padding = '';
		    for (var i = 0; i < pad; i++) {
		        padding += pad_content;
		    }

		    formatted += padding + node + '\r\n';
		    pad += indent;
		});

		return formatted;
	}
	
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	  
	// the mainline
	$(document).ready(function() {
        if ($(".api_logs").length == 0) {
            return;
        }
    add_API_Logs_page_listeners();
	window_resized();
	$(window).resize(window_resized);

	});
	
}(jQuery));

	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	///////////////////////////////////////////////////////////////////////////

// Polyfill for string.includes. See https://developer.mozilla.org/en/docs/Web/JavaScript/Reference/Global_Objects/String/includes
;String.prototype.includes||(String.prototype.includes=function(t,e){"use strict";return"number"!=typeof e&&(e=0),e+t.length>this.length?!1:-1!==this.indexOf(t,e)});

