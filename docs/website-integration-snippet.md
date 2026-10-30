<!-- ========================================================================= -->
<!-- NIEL INDUSTRIAL INTELLIGENCE AI - WEBSITE INTEGRATION SNIPPET            -->
<!-- Add this code into an Elementor HTML Widget or directly before </body>    -->
<!-- ========================================================================= -->

<script>
  window.NIEL_AI_CONFIG = {
    // Replace with your production FastAPI backend URL
    apiBase: 'https://api.assistant.newindiaelectricals.com',
    title: 'NIEL Industrial Assistant',
    subtitle: 'Grounded Technical Assistant',
    primaryColor: '#003366',
    accentColor: '#0284c7',
    position: 'bottom-right'
  };
</script>

<!-- Load the self-contained Shadow-DOM encapsulated widget -->
<script 
  src="https://assistant.newindiaelectricals.com/widget/niel-widget.js" 
  async 
  defer>
</script>
