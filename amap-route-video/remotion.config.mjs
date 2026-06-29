import {existsSync} from 'node:fs';
import {Config} from '@remotion/cli/config';

const chromePath = process.env.REMOTION_BROWSER_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

Config.setVideoImageFormat('png');
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
Config.setDelayRenderTimeoutInMilliseconds(120000);

if (existsSync(chromePath)) {
  Config.setBrowserExecutable(chromePath);
}
