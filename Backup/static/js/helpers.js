function $(selector, parent = document) {
  return parent.querySelector(selector);
}
function $all(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}
