// Javascript for the recipes. Some of the following is recipe specific
// other methods are generic

// 010.webhook.js
// JavaScript helper for the 010.webhook recipe
// This is NOT the Node.js recipe!
;(function ($) {
  
  	// page-level parameters are set via ds_params.
	// Eg {'navbar' : 'li_home'}
    // ds_params is set by the page as a script tag when the page is loaded.
	// 
	// Private global variabls for the functions
	var toc_items = [], // array of the notification items that are being displayed
		// The array is in normal sort order -- latest item is at the end
		envelope_terminal_statuses = ["Completed", "Declined", "Voided", 
			"AuthoritativeCopy", "TransferCompleted", "Template"],
	 	countdown_interval_id = false,
		countdown_i,
		ace_editor = false; 
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
    //
    // Page specific JS
    // Framework Home Page
    function framework_home_page() {
        if ($(".framework-home-page").length == 0) {
            return;
        }
        set_redirect_urls();
        home_auth_start();
    }

    function set_redirect_urls(){
        var redirect_uri = "auth_redirect",
            location = window.location,
            url = location.protocol + '//' + location.host + location.pathname + redirect_uri;

        $("#code_redirect_uri, #implicit_redirect_uri").val(url);
    }

	function home_auth_start(){
		// Queries the server to determine authentication status
		// If authenticated, set status
		// Else set status and enable user to submit authentication information
		var auth_status_url = "auth",
            target = "#home-auth",
            auth_params = "#auth-params",
            busy = "#busy",
            recipe_index = "#recipe-index",
            unauthenticate = "#unauthenticate";
        $.ajax({url: auth_status_url + "?" + Date.now()})
			.done(function(data, textStatus, jqXHR) {
                $(target).html(data.description);
                if (data.authenticated) {
                    $(recipe_index).show();
                    $(unauthenticate).show();
                } else {
                    $(auth_params).show()
                }
			})
			.fail(function(jqXHR, textStatus, errorThrown) {
			    $(target).html("<h3>Problem</h3><p>" + textStatus + "</p>");
			})
            .always(function(){
                $(busy).hide();
            })
	}

	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////

	function set_up_spin_links() {
		// For any "a" or "button" elements with data-do-spin="_id_", add an on_click
		// listener that will start up a spinner when the link is clicked
		var spin_listener = function(e){
			var spinner = e.data;
			$("#" + spinner).show("linear", 1000);
		};

		$('button[data-do-spin], a[data-do-spin]').each(
			function add_spin_listenr (i, el){
            	var spinner = $(el).attr( "data-do-spin" );
            	$(el).click(spinner, spin_listener);
        })
	}

    function set_up_countdown_feedback(){
        // data-count-feedback="feedback1"

        var count_feedback_click = function (e){
            var feedback = e.data,
                counter_el = $("#" + feedback).children().first().children().first(),
                countdown = function(){countdown_i -= 1; counter_el.text(countdown_i)},
                countdown_id;

            countdown_i = 100;
            $("#" + feedback).show();
            counter_el.text(countdown_i);
		    countdown_id = setInterval(countdown, 300);
        }

        $('[data-count-feedback]').each(function each_count_feedback (i, el){
            var feedback = $(el).attr( "data-count-feedback" );
            $(el).click(feedback, count_feedback_click);
        })
    }

    function set_ajax_buttons() {
        // An example button: 
        // <button id="startbtn" type="button" class="btn btn-primary"
        // data-endpoint="login" data-response="newpage_get">Login!</button>
        //
        // data-endpoint is the url for the new page or ajax call
        // data-response sets details on how to handle the req and response
        //    newpage_get simply loads the endpoint page
        //    Other than newpage_get: do an Ajax call
        //    Ajax Verb: POST, except for auth_delete which does a DELETE
        //  data-feedback the id of the Feedback html. If not present, then one will be created
        //
        // 1. set an on-click listener
        // 2. Add extra html after the button
        var feedback_html = 
            "<div class='feedback' style='display:none;'><h3>Working...&nbsp;&nbsp;&nbsp;<span></span></h3></div>";

        $('button[data-response]').each(function each_ajax_button (i, el){
            var feedback = $(el).attr( "data-feedback" );
            if (feedback === undefined) {
                $(el).parent().after(feedback_html);
            }
            $(el).click(ajax_click);
        })
    }
    
    var ajax_click = function (e){
        // The user clicked a button
        var el = event.target,
            endpoint = $(el).attr( "data-endpoint" ),
            response = $(el).attr( "data-response" ),
            verb = response == "auth_delete" ? "delete" : "post",
            feedback = $(el).attr( "data-feedback" ),
            feedback_el = (feedback === undefined) ? $(el).parent().next() : $("#" + feedback),
            counter_el = feedback_el.children().first().children().first(),
            countdown = function(){countdown_i -= 1; counter_el.text(countdown_i)},
            countdown_id
        ;
        
        countdown_i = 100;
        button_disable(el);
        feedback_el.show();
        counter_el.text(countdown_i);
		countdown_id = setInterval(countdown, 300);
        
        // newpage responses: simply transfer over to the new page
        if (response==="newpage_get") {
            window.location = endpoint;
        } else {
            send_ajax_click(el, endpoint, response, feedback_el, verb);
        }
    }

    function send_ajax_click(button, endpoint, response, feedback_el, verb){
        // endpoint is the url
        // response tells us about the request, how to handle, etc

        var form = $(button).closest("form"),
            req_data = $(form).serializeJSON(),
            home_auth = "#home-auth",
            auth_params = "#auth-params",
            recipe_index = "#recipe-index",
            unauthenticate = "#unauthenticate";

        var ajax_done = function (data, textStatus, jqXHR) {
            if (response === "auth") {
                // Requesting authentication
                if (data.err) {
                    $(feedback_el).html("<h3>Problem</h3><p>" + data.err + "</p>");
                    return;
                }
                if (data.redirect) {
                    window.location = data.redirect;
                    return;
                }
                // No data.err therefore success!
                $(home_auth).html(data.auth_status.description);
                $(auth_params).hide();
                $(recipe_index).show();
                $(unauthenticate).show();
            } else if (response === "auth_delete") {
                window.location.reload();
            }
        }

        $.ajax({
			url: endpoint,
           	type: verb,
            data: req_data,
            contentType: "application/json; charset=utf-8",
			dataType: "json"
			})
			.done(ajax_done)
			.fail(function(jqXHR, textStatus, errorThrown) {
			    $(feedback_el).html("<h3>Problem</h3><p>" + textStatus + "</p>");
			})
            .always(function(){
				button_enable(button);
                // Delay 20 seconds, then $(feedback_el).hide();
            })
        }


        
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////

	function set_nav_bar () {
		// Uses the navbar element of ds_params
		if (typeof ds_params !== 'undefined' && ds_params !== null 
			&& typeof ds_params === 'object' && ds_params.navbar !== undefined ) {
			
			$('#' + ds_params.navbar).addClass("active");
		}
	}
	
	function set_on_send_btn() {
		// params:
		// 'send_param' => ["ds_signer1_name"  => $connect_lib->ds_signer1_name,
		// 				 "ds_signer1_email" => $connect_lib->ds_signer1_email,
		// 				 "button" => "sendbtn",
		// 				 "url" => "010.connect.php?op=send2",
		// 				 "target" => "target"]

		if (typeof ds_params === 'undefined' || ds_params == null 
			|| typeof ds_params !== 'object' || typeof ds_params.send_param === 'undefined' ) {
				return; // EARLY return, nothing to do here!
		}
		
		// All's good
		var send_param = ds_params.send_param,
			button = "#" + send_param.button,
			url = send_param.url,
			target = "#" + send_param.target;
		
		$(button).click(function() {
			button_disable(button);
			$(target).html("<p>Working...</p>");
			$.ajax({
				url: url,
           		type: 'post',
            	data: JSON.stringify(send_param),
            	contentType: "application/json; charset=utf-8",
				dataType: "json"
			})
			.done(function(data, textStatus, jqXHR) {
				button_enable(button);
			    $(target).html(data.html);
				js_requests(data); // nb. may disable the button
			})
			.fail(function(jqXHR, textStatus, errorThrown) {
				button_enable(button);
			    $(target).html("<h3>Problem</h3><p>" + textStatus + "</p>");
			})
		});
	}
		
	function js_requests(data) {
		// Look for a js field. If it exists, handle...
		// So far, just handling
		//   'js' => ['disable_button' => 'sendbtn']];
		if (data.hasOwnProperty('js')) {
			data.js.forEach(js_request);
		}
	}
	
	function js_request(element, index, array) {
		// So far, just handling
		//   'js' => ['disable_button' => 'sendbtn']];
		if (element.hasOwnProperty('disable_button')) {
			button_disable("#" + element.disable_button);
		}
	}
	
	function button_disable(id) {
		$(id).attr("disabled", "disabled");
	}
	
	function button_enable(id) {
		$(id).removeAttr("disabled");			
	}
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	//
	// Functions for showing the incoming events
	// Add envelope info to #env_info
	// The left column ul is #toc, the main column uses xml_info for info and feedback
	
	function show_status() {
		if (typeof ds_params === 'undefined' || ds_params === null 
			|| typeof ds_params !== 'object' 
			|| typeof ds_params.status_envelope_id === 'undefined'
			|| !ds_params.status_envelope_id) {
				return;
		}
		
		// We're good to go!
		var envelope_id = ds_params.status_envelope_id,
			interval_id;
		
		// Keep the humans occupied..
		countdown_interval_id = setInterval(countdown, 300);
		
		var fetch_latest = function (){
			// This function fetches the latest info from the server
			working_show();
			$.ajax({
				url: ds_params.url + "/status_items/" + envelope_id,
            	contentType: "application/json; charset=utf-8",
				dataType: "json"
			})
			.done(function(data, textStatus, jqXHR) {
				var stop_fetching = process_items(data.items);
				if (stop_fetching) {
					clearInterval(interval_id);
				}
			})
			.always(function() {working_hide();})
		}
		
		// The main stem...
		window_resized();
		$(window).resize(window_resized);
		interval_id = setInterval(fetch_latest, 3000);
	}
		
	function process_items(data){
		// Process the list of items
		// The data is an array of events. Events are objects
		// [event]
		// event :: 
		// { envelope_id,
		//	 time_generated,
		//   subject
		//	 sender_user_name
		//	 sender_email
		//	 envelope_status
		//	 timezone_offset
		//   recipients: [recipient]
		//   documents: [document]	
		// }	
		//
		// recipient ::
		// { type
		//	 email
		//	 user_name
		//	 routing_order
		//	 sent_timestamp
		//	 status
		// }
		//
		// document ::
		// { document_ID
		//   document_type
		//   name
		//   url 
		// }
		// RETURNS stop_fetch -- should we stop querying?
		
		if (data.length == 0) {return;} // nothing to do...
		stop_countdown();
		
		// Sort the incoming events
		data.sort(function (a, b) {
  			// compare time_generated eg 2016-01-01T01:07:04.1479113
			var a_parts = a.time_generated.split('.'),
				b_parts = b.time_generated.split('.'),
				a_datetime = new Date(a_parts[0]),
				b_datetime = new Date(b_parts[0]);
			if (a_datetime > b_datetime) {return 1;}
			if (a_datetime < a_datetime) {return -1;}
			if (a_parts[1] > b_parts[1]) {return 1;}
			if (a_parts[1] < b_parts[1]) {return -1;}
			return 0; // a must be equal to b
	  	});
	
		// remove incoming items that we aleady know about
		var data_new  = data.filter (function (val, index, arr){
			return !toc_items.find(function (element, i, a){
				return val.time_generated == element.time_generated;
			});
		});
		
		if (data_new.length == 0) {return;} // nothing to do...
	
		// display the new data
		data_new.forEach (function(val, index, arr){add_to_toc(val);});
		var latest = data_new[data_new.length - 1];
		
		return envelope_terminal_statuses.includes(latest.envelope_status); // envelope done?
	}
	
	function add_to_toc(item){
		// Augment the incoming data by comparing it with the prior data
		var toc_items_latest = toc_items.length > 0 ? toc_items[toc_items.length - 1] : false,
			status_class_new_data = "newdata",
			status_class_same_data = "";
    	
		// add envelope_status_class
		if (toc_items_latest) {
			item.envelope_status_class = (item.envelope_status == toc_items_latest.envelope_status) ? 
				status_class_same_data : status_class_new_data;
		} else {
			item.envelope_status_class = status_class_new_data;
		}
    	
		// add status_class for each recipient
		item.recipients.forEach (function(val, index, arr){
			if (toc_items_latest) {
				previous = toc_items_latest.recipients.find(function (element, i, a){
					return val.email == element.email &&
						val.user_name == element.user_name && // the same email can be two different user_names eg: a couple
						val.type == element.type && // Eg a person can be both a signer and later receive a specific cc or cd
						val.routing_order == element.routing_order ; // Eg, a person could sign twice, once after someone else
				});
				
				if (previous) {
					val.status_class = (val.status == previous.status) ? 
						status_class_same_data : status_class_new_data;
				} else {
					val.status_class = status_class_new_data;
				} 
			} else {
				val.status_class = status_class_new_data;
			}
		});
	
		toc_items.push(item); // We're assuming that we won't receive an item out of order.
		// Create the new li by using mustache with the template
	    var rendered = Mustache.render($('#toc_item_template').html(), item);
		prependListItem("toc", rendered);
		// The new item is now the first item in the toc ul.
		$("#toc").children().first().click(item, show_xml);
	}
	
	// prependListItem("test", "<li>The new item</li>");
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

	var show_xml = function(event) {
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
		set_nav_bar();
		set_on_send_btn();
		// show_xml({data: {xml_url: "foo.xml"}}); // For testing: loads local foo.xml
		show_status();
        set_ajax_buttons();
		set_up_spin_links();
        set_up_countdown_feedback();
        
        // page specific JS
        framework_home_page();
	});
	
	
	
}(jQuery));

	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////

// Array.foreach polyfill
// From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach
Array.prototype.forEach||(Array.prototype.forEach=function(r,t){var o,n;if(null==this)throw new TypeError(" this is null or not defined");var e=Object(this),i=e.length>>>0;if("function"!=typeof r)throw new TypeError(r+" is not a function");for(arguments.length>1&&(o=t),n=0;i>n;){var a;n in e&&(a=e[n],r.call(o,a,n,e)),n++}});
// Array.find polyfill
Array.prototype.find||(Array.prototype.find=function(r){if(null===this)throw new TypeError("Array.prototype.find called on null or undefined");if("function"!=typeof r)throw new TypeError("predicate must be a function");for(var t,n=Object(this),e=n.length>>>0,o=arguments[1],i=0;e>i;i++)if(t=n[i],r.call(o,t,i,n))return t});
// Array.includes polyfill
Array.prototype.includes||(Array.prototype.includes=function(r){"use strict";var t=Object(this),e=parseInt(t.length)||0;if(0===e)return!1;var n,a=parseInt(arguments[1])||0;a>=0?n=a:(n=e+a,0>n&&(n=0));for(var s;e>n;){if(s=t[n],r===s||r!==r&&s!==s)return!0;n++}return!1});

/**
 * jQuery serializeObject
 * @copyright 2014, macek <paulmacek@gmail.com>
 * @link https://github.com/macek/jquery-serialize-object
 * @license BSD
 * @version 2.5.0
 */
!function(e,i){if("function"==typeof define&&define.amd)define(["exports","jquery"],function(e,r){return i(e,r)});else if("undefined"!=typeof exports){var r=require("jquery");i(exports,r)}else i(e,e.jQuery||e.Zepto||e.ender||e.$)}(this,function(e,i){function r(e,r){function n(e,i,r){return e[i]=r,e}function a(e,i){for(var r,a=e.match(t.key);void 0!==(r=a.pop());)if(t.push.test(r)){var u=s(e.replace(/\[\]$/,""));i=n([],u,i)}else t.fixed.test(r)?i=n([],r,i):t.named.test(r)&&(i=n({},r,i));return i}function s(e){return void 0===h[e]&&(h[e]=0),h[e]++}function u(e){switch(i('[name="'+e.name+'"]',r).attr("type")){case"checkbox":return"on"===e.value?!0:e.value;default:return e.value}}function f(i){if(!t.validate.test(i.name))return this;var r=a(i.name,u(i));return l=e.extend(!0,l,r),this}function d(i){if(!e.isArray(i))throw new Error("formSerializer.addPairs expects an Array");for(var r=0,t=i.length;t>r;r++)this.addPair(i[r]);return this}function o(){return l}function c(){return JSON.stringify(o())}var l={},h={};this.addPair=f,this.addPairs=d,this.serialize=o,this.serializeJSON=c}var t={validate:/^[a-z_][a-z0-9_]*(?:\[(?:\d*|[a-z0-9_]+)\])*$/i,key:/[a-z0-9_]+|(?=\[\])/gi,push:/^$/,fixed:/^\d+$/,named:/^[a-z0-9_]+$/i};return r.patterns=t,r.serializeObject=function(){return new r(i,this).addPairs(this.serializeArray()).serialize()},r.serializeJSON=function(){return new r(i,this).addPairs(this.serializeArray()).serializeJSON()},"undefined"!=typeof i.fn&&(i.fn.serializeObject=r.serializeObject,i.fn.serializeJSON=r.serializeJSON),e.FormSerializer=r,r});



