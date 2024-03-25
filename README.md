# geOrchestra analytics module

The geOrchestra statistics module analyzes logs provided by the Gateway module, processes them to extract information and constructs statistics.
The data is stored in a database using the TimeScaleDB plugin. Visualization is provided by dashboards powered by SuperSet.

Read the notes contained in the 'notes' directory.


## Principle

The geOrchestra gateway is a unique point of entry in the geOrchestra SDI. It is a sort of reverse-proxy forwarding the requests to the different modules, depending on the request path / application. It also applies security rules.

The geOrchestra gateway is core as it is the only point that knows all about the identity of the authentified users and their requests.

The Analytics module expects some specific access logs from the gateway to treat.


## Analytics log format

The analytics module expect a text file log from the gateway, not JSON.

A line of the log is divided in x parts. Each part is separated by a pipe `|`.

| Part                   | Analytics variable     | Description                                                                                           | Example                                                                                                                                                                                                                                                                              |
|------------------------|------------------------|-------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IP                     | ip                     | IP adress of the requestor                                                                            | 8.8.8.8                                                                                                                                                                                                                                                                              |
| Date time              | date_time              | The date + time of the access in common log format. The time is in UTC or with a time zone indicator. | 24/Jan/2021:06:25:21 +0100                                                                                                                                                                                                                                                           |
| User login             | user_login             | The user login.                                                                                       | m.lagadec                                                                                                                                                                                                                                                                            |
| User organization      | user_org               | The name of the user organization.                                                                    | Région Bretagne                                                                                                                                                                                                                                                                      |
| User roles             | user_roles             | The list of the geOrchestra LDAP roles. These roles are used to manage rights access control.         | ROLE_USER,EL_ROLE_SERVICE_X,EL_ROLE_APP_Y                                                                                                                                                                                                                                            |
| HTTP method            | http_method            | The HTTP method.                                                                                      | GET / PUT / POST, etc                                                                                                                                                                                                                                                                |
| HTTP request           | http_request           | The HTTP request.                                                                                     | /geoserver/espub_dech/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=v_gesbac_pav&STYLES=v_gesbac_pav&TILED=true&WIDTH=256&HEIGHT=256&CRS=EPSG%3A3857&BBOX=-156543.03392804042%2C6085610.443952592%2C-136975.1546870353%2C6105178.323193598 |
| HTTP status code       | http_status_code       | The HTTP status code.                                                                                 | 200 / 404 / 500                                                                                                                                                                                                                                                                      |
| HTTP response duration | http_response_duration | The time needed by the SDI to send the answer of the request. In seconds.                             | 0.254                                                                                                                                                                                                                                                                                |
| HTTP response size     | http_response_size     | The size of the data send to the requestor. In bytes.                                                 | 3512                                                                                                                                                                                                                                                                                 |
| User agent             | user_agent             | The web brower or client who does the request.                                                        | Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0                                                                                                                                                                                                                                                                                   |


Example : `xxx.xxx.0.1|24/Jan/2021:06:25:21 +0100|m.lagadec|Région Bretagne|ROLE_USER,EL_ROLE_SERVICE_X,EL_ROLE_APP_Y
|GET|http://geonetwork:8080/geonetwork/srv/eng/catalog.search|200|0.254|Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0`







