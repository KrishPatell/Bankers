/* Appointment form behaviour for contact-us.html and the two public booking
 * aliases. The form stays on the existing /api/contact lead path; this script
 * only manages configurable city schedules, route preselection and validation.
 */
(function () {
  "use strict";

  var form = document.querySelector("form[data-appointment-form]");
  if (!form) return;

  var citySelect = form.querySelector("[data-appointment-city]");
  var diseaseSelect = form.querySelector("[data-appointment-disease]");
  var dateInput = form.querySelector("[data-appointment-date]");
  var timeSelect = form.querySelector("[data-appointment-time]");
  var callbackInput = form.querySelector("[data-appointment-callback]");
  var consentInput = form.querySelector("[data-appointment-consent]");
  var status = form.querySelector("[data-appointment-status]");
  if (!citySelect || !diseaseSelect || !dateInput || !timeSelect || !callbackInput || !consentInput) return;

  var availableDates = [];
  var today = localDateString(new Date());
  var routeCity = cityFromUrl();
  var fallbackConfig = {
    cities: Array.prototype.map.call(citySelect.options, function (option) {
      return { name: option.value, active: Boolean(option.value) };
    }).filter(function (item) { return item.name; }),
    diseases: Array.prototype.map.call(diseaseSelect.options, function (option) {
      return option.value;
    }).filter(Boolean),
    schedules: {}
  };

  function localDateString(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, "0");
    var day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function cityFromUrl() {
    var queryCity = "";
    try {
      queryCity = new URLSearchParams(window.location.search).get("city") || "";
    } catch (_) {}
    var pathMatch = window.location.pathname.match(/\/book-appointment\/([^/]+)\/?$/i);
    var pathCity = "";
    if (pathMatch) {
      try { pathCity = decodeURIComponent(pathMatch[1]); } catch (_) { pathCity = pathMatch[1]; }
      pathCity = pathCity.replace(/[-_]+/g, " ");
    }
    var value = queryCity || pathCity;
    if (!value) return "";
    return value.replace(/\b\w/g, function (letter) { return letter.toUpperCase(); });
  }

  function option(select, value, label, disabled) {
    var item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    if (disabled) item.disabled = true;
    select.appendChild(item);
  }

  function renderCities(items, selected) {
    var active = (items || []).filter(function (item) {
      return typeof item === "string" || item.active !== false;
    }).map(function (item) {
      return typeof item === "string" ? item : item.name;
    }).filter(Boolean);
    if (!active.length) return;
    citySelect.innerHTML = "";
    option(citySelect, "", "Select your city", true);
    active.forEach(function (city) { option(citySelect, city, city, false); });
    citySelect.value = active.some(function (city) { return normalize(city) === normalize(selected); }) ? selected : "";
  }

  function renderDiseases(items, selected) {
    var diseases = (items || []).filter(Boolean);
    if (!diseases.length) return;
    diseaseSelect.innerHTML = "";
    option(diseaseSelect, "", "Select a disease or condition", true);
    diseases.forEach(function (disease) { option(diseaseSelect, disease, disease, false); });
    diseaseSelect.value = diseases.indexOf(selected) >= 0 ? selected : "";
  }

  function scheduleFor(config, city) {
    var schedules = config && config.schedules ? config.schedules : {};
    return schedules[city] || { dates: [], timings: [], note: "" };
  }

  function validFutureDates(schedule) {
    return (schedule.dates || []).filter(function (value) {
      return /^\d{4}-\d{2}-\d{2}$/.test(String(value)) && String(value) >= today;
    }).sort();
  }

  function formatDate(value) {
    var parts = String(value).split("-");
    if (parts.length !== 3) return value;
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }

  function updateTimeOptions(schedule) {
    var timings = (schedule.timings || []).filter(Boolean);
    timeSelect.innerHTML = "";
    option(timeSelect, "", timings.length ? "Select a preferred time" : "Timing will be confirmed by hospital team", false);
    timings.forEach(function (timing) { option(timeSelect, timing, timing, false); });
    timeSelect.value = "";
  }

  function setStatus(message) {
    if (status) status.textContent = message;
  }

  function updateSchedule(config) {
    var city = citySelect.value;
    var schedule = scheduleFor(config, city);
    var dates = validFutureDates(schedule);
    availableDates = dates;
    dateInput.value = "";
    dateInput.min = today;
    dateInput.setCustomValidity("");
    callbackInput.setCustomValidity("");
    updateTimeOptions(schedule);

    if (!city) {
      dateInput.disabled = true;
      dateInput.required = false;
      callbackInput.required = false;
      setStatus("Select a city to see currently configured consultation dates.");
      return;
    }

    if (dates.length) {
      dateInput.disabled = false;
      dateInput.required = true;
      callbackInput.required = false;
      setStatus("Available consultation dates: " + dates.map(formatDate).join(", ") + ". Timing will be confirmed by the hospital team.");
    } else {
      dateInput.disabled = true;
      dateInput.required = false;
      callbackInput.required = true;
      setStatus(schedule.note || "No consultation date is currently published for this city. Select callback request and our hospital team will help.");
    }
  }

  function validateDate() {
    if (dateInput.disabled || !dateInput.value) {
      dateInput.setCustomValidity("");
      return;
    }
    if (dateInput.value < today) {
      dateInput.setCustomValidity("Please choose today or a future date.");
    } else if (availableDates.length && availableDates.indexOf(dateInput.value) === -1) {
      dateInput.setCustomValidity("Please select one of the currently published consultation dates.");
    } else {
      dateInput.setCustomValidity("");
    }
  }

  function validateAppointment() {
    validateDate();
    if (dateInput.disabled && !callbackInput.checked) {
      callbackInput.setCustomValidity("Please request a callback because no consultation date is currently published.");
    } else {
      callbackInput.setCustomValidity("");
    }
    if (!form.checkValidity()) {
      if (typeof form.reportValidity === "function") form.reportValidity();
      return false;
    }
    return true;
  }

  form.__validateAppointment = validateAppointment;
  form.__appointmentConfig = fallbackConfig;
  dateInput.min = today;
  dateInput.disabled = true;
  dateInput.required = false;

  citySelect.addEventListener("change", function () { updateSchedule(form.__appointmentConfig); });
  dateInput.addEventListener("change", validateDate);
  callbackInput.addEventListener("change", function () { callbackInput.setCustomValidity(""); });

  renderCities(fallbackConfig.cities, routeCity);
  renderDiseases(fallbackConfig.diseases, diseaseSelect.value);
  updateSchedule(fallbackConfig);

  fetch("/data/appointment-config.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("Appointment config unavailable");
      return response.json();
    })
    .then(function (config) {
      var selectedCity = citySelect.value || routeCity;
      var selectedDisease = diseaseSelect.value;
      form.__appointmentConfig = config;
      renderCities(config.cities, selectedCity);
      renderDiseases(config.diseases, selectedDisease);
      updateSchedule(config);
    })
    .catch(function () {
      /* The HTML keeps the complete city/disease list as a no-JS fallback. */
    });
}());
