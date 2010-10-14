dojo.provide("nox.ext.apps.coreui.coreui.png");

(function(){
	//a fix for transparent png in ie6
	 
	if (dojo.isIE && dojo.isIE < 7 &&  document.styleSheets && document.styleSheets[0] && document.styleSheets[0].addRule){
		var fixUrl = dojo.moduleUrl("nox.ext.apps.coreui.coreui.png", "iepngfix.htc");
		document.styleSheets[0].addRule('*', 'behavior: url("' + fixUrl.path + '")');
	}
})();
