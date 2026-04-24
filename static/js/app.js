document.querySelectorAll('.alert').forEach(a=>setTimeout(()=>bootstrap.Alert.getOrCreateInstance(a).close(),4000));
